import time
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from countries.models import Country
from pricing.models import Pricing, PricingConfiguration
from providers.smsbower import SMSBowerProvider
from services.models import Service

# ISO codes for display on the buy page (server1 only needs the top markets)
ISO_MAP = {
    "united states": "US", "united kingdom": "GB", "nigeria": "NG",
    "canada": "CA", "ghana": "GH", "south africa": "ZA", "india": "IN",
    "philippines": "PH", "kenya": "KE", "germany": "DE", "france": "FR",
    "netherlands": "NL", "spain": "ES", "italy": "IT", "ireland": "IE",
    "poland": "PL", "sweden": "SE", "belgium": "BE", "austria": "AT",
    "portugal": "PT", "australia": "AU", "new zealand": "NZ", "brazil": "BR",
    "mexico": "MX", "indonesia": "ID", "malaysia": "MY", "thailand": "TH",
    "korea": "KR", "japan": "JP", "china": "CN", "russian federation": "RU",
    "ukraine": "UA", "united arab emirates": "AE", "saudi arabia": "SA",
    "egypt": "EG", "turkey": "TR", "argentina": "AR", "colombia": "CO",
    "viet nam": "VN", "bangladesh": "BD", "pakistan": "PK",
}

# --- WHATSAPP CHEAPEST-VARIANT + PINNED PROVIDER ID -------------------------
# For each country listed here, the main "WhatsApp" service row on server1:
#   * price  = the CHEAPEST in-stock WhatsApp variant SMSBower offers for that
#     country (out-of-stock variants are ignored when picking)
#   * provider_id in provider_meta = the pinned value below, ALWAYS,
#     no matter what the sync fetches
# Add more countries like:  "united kingdom": 1234,
WHATSAPP_PIN = {
    "united states": 3535,
}
WHATSAPP_EXCLUDE_BUSINESS = True   # ignore "WhatsApp Business" variants
CANONICAL_WHATSAPP_NAME = "whatsapp"  # the main WhatsApp service name on server1


def to_ngn(usd, config):
    """cost_ngn = usd * exchange_rate (NO rounding),
    selling = cost_ngn + fixed_profit"""
    cost = Decimal(str(usd)) * config.exchange_rate
    return cost, cost + config.fixed_profit


class Command(BaseCommand):
    help = "Sync SMSBower countries, services and prices into server1 (bulk V3 endpoint)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--countries",
            type=str,
            default="",
            help="Comma-separated country names to sync (default: all)",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.5,
            help="Delay between country price calls (default 0.5s)",
        )

    def handle(self, *args, **options):
        provider = SMSBowerProvider()

        config = PricingConfiguration.objects.first()
        if not config:
            raise CommandError(
                "No PricingConfiguration row found. Create one in admin first."
            )

        # ---------------- COUNTRIES -> server1 (1 call) ----------------
        data = provider.get_countries()
        rows = data if isinstance(data, list) else [
            {"id": cid, **names} for cid, names in data.items()
            if isinstance(names, dict)
        ]
        for c in rows:
            cid = str(c.get("id", "")).strip()
            name = (c.get("eng") or "").strip()
            if not cid.isdigit() or not name:
                continue
            cid_int = int(cid)
            # Never empty - unique(iso_code, server) rejects duplicate ""
            iso = ISO_MAP.get(name.lower()) or f"SB{cid}"

            obj = Country.objects.filter(
                server="server1", provider_id=cid_int).first()
            if obj:
                obj.name, obj.iso_code, obj.status = name, iso, "active"
                obj.save(update_fields=["name", "iso_code", "status"])
            else:
                # Adopt a kept InstantNums row with the same name instead of
                # creating a duplicate (unique name+server)
                obj = Country.objects.filter(server="server1", name=name).first()
                if obj:
                    obj.provider_id = cid_int
                    obj.iso_code = iso
                    obj.status = "active"
                    obj.save(update_fields=["provider_id", "iso_code", "status"])
                else:
                    Country.objects.create(
                        server="server1", provider_id=cid_int,
                        name=name, iso_code=iso, status="active",
                    )
        self.stdout.write(self.style.SUCCESS(f"Countries synced: {len(rows)}"))

        # ---------------- SERVICES -> server1 (1 call) ----------------
        services = provider.get_services()
        seen_codes = set()
        skipped = 0
        for s in services:
            code = str(s.get("code", "")).strip().lower()[:100]
            name = str(s.get("name", "")).strip()[:255]
            if not code or not name:
                continue

            # 1. Match by code -> just refresh
            obj = Service.objects.filter(server="server1", code=code).first()
            if obj:
                obj.name, obj.status = name, "active"
                obj.save(update_fields=["name", "status"])
                seen_codes.add(code)
                continue

            # 2. unique(name, server): adopt an existing row with this name
            #    whose code isn't claimed by another SMSBower service
            obj = Service.objects.filter(server="server1", name=name).first()
            if obj and obj.code not in seen_codes:
                obj.code, obj.status = code, "active"
                obj.save(update_fields=["code", "status"])
                seen_codes.add(code)
                continue

            # 3. Name taken by something else (or duplicate name in provider
            #    list) - skip rather than crash
            if Service.objects.filter(server="server1", name=name).exists():
                self.stdout.write(self.style.WARNING(
                    f"  Skipped service {code} ({name}): name already on server1"
                ))
                skipped += 1
                continue

            Service.objects.create(server="server1", code=code,
                                   name=name, status="active")
            seen_codes.add(code)

        self.stdout.write(self.style.SUCCESS(
            f"Services synced: {len(seen_codes)} (skipped {skipped})"
        ))

        # Deactivate server1 services SMSBower doesn't offer (InstantNums leftovers)
        stale = Service.objects.filter(server="server1").exclude(code__in=seen_codes)
        stale_count = stale.update(status="inactive")
        if stale_count:
            self.stdout.write(f"Deactivated {stale_count} old server1 services")

        # ---------------- PRICES (1 bulk V3 call per country) ----------------
        qs = Country.objects.filter(server="server1", status="active")
        if options["countries"]:
            wanted = [x.strip() for x in options["countries"].split(",") if x.strip()]
            qs = qs.filter(name__in=wanted)

        total = qs.count()
        self.stdout.write(f"Fetching bulk prices for {total} countries...")

        ok = unavailable = failed = 0
        for i, ctry in enumerate(qs, 1):
            try:
                prices = provider.get_prices_by_country_id(ctry.provider_id)
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"  [{i}/{total}] {ctry.name}: fetch failed ({e})"
                ))
                failed += 1
                time.sleep(options["sleep"])
                continue

            pin_id = WHATSAPP_PIN.get(ctry.name.lower())
            canon_wa = None
            wa_variants = []

            seen_service_ids = set()
            for code, info in prices.items():
                svc = Service.objects.filter(server="server1", code=code).first()
                if not svc:
                    continue
                seen_service_ids.add(svc.id)

                # Collect WhatsApp variants for the cheapest-variant logic
                if CANONICAL_WHATSAPP_NAME in svc.name.lower() and (
                    not WHATSAPP_EXCLUDE_BUSINESS
                    or "business" not in svc.name.lower()
                ):
                    if svc.name.lower() == CANONICAL_WHATSAPP_NAME:
                        canon_wa = svc
                    wa_variants.append(
                        (Decimal(str(info["cost"])), info.get("count", 0), info)
                    )

                cost_ngn, sell_ngn = to_ngn(info["cost"], config)
                Pricing.objects.update_or_create(
                    country=ctry,
                    service=svc,
                    defaults={
                        "provider_cost": cost_ngn,
                        "selling_price": sell_ngn,
                        "is_available": info.get("count", 0) > 0,
                        "status": "active",
                        "provider_meta": {
                            "provider_id": info.get("provider_id"),
                            "cost_usd": info["cost"],
                        },
                    },
                )
                ok += 1

            # --- PINNED WHATSAPP: cheapest in-stock variant's price,
            #     pinned provider id, on the main WhatsApp row ---
            if pin_id and wa_variants:
                in_stock = [v for v in wa_variants if v[1] > 0]
                pool = in_stock or wa_variants  # fall back to cheapest overall
                cost_usd, cnt, cheapest_info = min(pool, key=lambda v: v[0])

                if not canon_wa:
                    canon_wa = Service.objects.filter(
                        server="server1", name__iexact=CANONICAL_WHATSAPP_NAME
                    ).first()

                if canon_wa:
                    cost_ngn, sell_ngn = to_ngn(cost_usd, config)
                    Pricing.objects.update_or_create(
                        country=ctry,
                        service=canon_wa,
                        defaults={
                            "provider_cost": cost_ngn,
                            "selling_price": sell_ngn,
                            "is_available": cnt > 0,
                            "status": "active",
                            "provider_meta": {
                                "provider_id": pin_id,
                                "cost_usd": cost_usd,
                            },
                        },
                    )
                    ok += 1
                    seen_service_ids.add(canon_wa.id)
                else:
                    self.stdout.write(self.style.WARNING(
                        f"  [{i}/{total}] {ctry.name}: WHATSAPP_PIN set but no "
                        f"'{CANONICAL_WHATSAPP_NAME}' service found on server1"
                    ))

            # Anything not in the response is out of stock -> unavailable
            marked = Pricing.objects.filter(
                country=ctry, service__server="server1"
            ).exclude(service_id__in=seen_service_ids).update(is_available=False)
            unavailable += marked

            if i % 10 == 0 or i == total:
                self.stdout.write(f"  [{i}/{total}] prices ok={ok} "
                                  f"unavailable={unavailable} failed={failed}")
            time.sleep(options["sleep"])

        self.stdout.write(self.style.SUCCESS(
            f"Done: {ok} prices synced, {unavailable} marked unavailable, "
            f"{failed} countries failed"
        ))