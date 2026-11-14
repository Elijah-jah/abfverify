import time
from decimal import Decimal, ROUND_HALF_UP

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


def to_ngn(usd, config):
    """Same pricing formula as Daisy (server2):
    cost_ngn = usd * exchange_rate, selling = cost_ngn + fixed_profit"""
    cost = (Decimal(str(usd)) * config.exchange_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return cost, cost + config.fixed_profit


class Command(BaseCommand):
    help = "Sync SMSBower countries, services and prices into server1 (bulk endpoint)"

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

        # ---------------- PRICES (1 bulk call per country) ----------------
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

            seen_service_ids = set()
            for code, info in prices.items():
                svc = Service.objects.filter(server="server1", code=code).first()
                if not svc:
                    continue
                seen_service_ids.add(svc.id)
                cost_ngn, sell_ngn = to_ngn(info["cost"], config)
                Pricing.objects.update_or_create(
                    country=ctry,
                    service=svc,
                    defaults={
                        "provider_cost": cost_ngn,
                        "selling_price": sell_ngn,
                        "is_available": info.get("count", 0) > 0,
                        "status": "active",
                    },
                )
                ok += 1

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