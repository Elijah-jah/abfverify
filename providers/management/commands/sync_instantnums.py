import time
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from countries.models import Country
from services.models import Service
from pricing.models import Pricing, PricingConfiguration
from providers.instantnums import InstantNumsProvider


def to_ngn(usd, config):
    """YOUR pricing formula — identical to Daisy (server2):
    cost_ngn = usd * exchange_rate
    selling  = cost_ngn + fixed_profit"""
    cost = (Decimal(str(usd)) * config.exchange_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return cost, cost + config.fixed_profit


class Command(BaseCommand):
    help = "Sync InstantNums countries, services and prices into server1"

    MAX_RETRIES = 3

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-prices",
            action="store_true",
            help="Only sync countries and services",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.25,
            help="Delay between price calls in seconds (rate-limit safety)",
        )
        parser.add_argument(
            "--services",
            type=str,
            default="",
            help="Comma-separated service codes to sync (default: all)",
        )
        parser.add_argument(
            "--countries",
            type=str,
            default="",
            help="Comma-separated country names to sync (default: all)",
        )
        parser.add_argument(
            "--resume",
            action="store_true",
            help="Skip pairs already synced within --max-age hours (continue an interrupted run)",
        )
        parser.add_argument(
            "--max-age",
            type=int,
            default=24,
            help="Hours before a synced price is considered stale (used with --resume)",
        )

    def handle(self, *args, **options):
        started = time.time()
        provider = InstantNumsProvider()

        config = PricingConfiguration.objects.first()
        if not config:
            raise CommandError(
                "No PricingConfiguration row found. Create one in admin first."
            )

        # ---------------- COUNTRIES -> server1 ----------------
        data = provider.get_countries()
        countries = data.get("countries", [])
        for c in countries:
            Country.objects.update_or_create(
                server="server1",
                provider_id=c["ID"],
                defaults={
                    "name": c["name"],
                    "iso_code": c.get("short_name", ""),
                    "phone_code": c.get("cc", ""),
                    "status": "active",
                },
            )
        self.stdout.write(self.style.SUCCESS(f"Countries synced: {len(countries)}"))

        # ---------------- SERVICES -> server1 ----------------
        data = provider.get_services()
        services = data.get("services", [])
        for s in services:
            raw = s["name"]
            code = raw[:100]
            if len(raw) > 100:
                self.stdout.write(self.style.WARNING(
                    f"Service name truncated ({len(raw)} chars): {raw}"
                ))

            defaults = {
                "code": code,
                "name": raw[:255],
                "status": "active",
            }

            sid = s.get("ID")
            if isinstance(sid, int):
                defaults["provider_id"] = sid
            elif isinstance(sid, str) and sid.isdigit():
                defaults["provider_id"] = int(sid)

            if "provider_id" in defaults:
                # Numeric ID: upsert by provider_id alone (globally unique).
                # Also adopts old rows imported under a different server label.
                pid = defaults.pop("provider_id")
                defaults["server"] = "server1"
                Service.objects.update_or_create(
                    provider_id=pid,
                    defaults=defaults,
                )
            else:
                # String IDs ('whatsapp_usa' etc.): no provider_id to match on
                Service.objects.update_or_create(
                    server="server1",
                    code=code,
                    defaults=defaults,
                )
        self.stdout.write(self.style.SUCCESS(f"Services synced: {len(services)}"))

        if options["skip_prices"]:
            return

        # ---------------- PRICES ----------------
        qs_countries = Country.objects.filter(server="server1")
        qs_services = Service.objects.filter(server="server1")

        if options["services"]:
            wanted = [x.strip() for x in options["services"].split(",") if x.strip()]
            qs_services = qs_services.filter(code__in=wanted)
        if options["countries"]:
            wanted = [x.strip() for x in options["countries"].split(",") if x.strip()]
            qs_countries = qs_countries.filter(name__in=wanted)

        total = qs_countries.count() * qs_services.count()
        if total == 0:
            self.stdout.write(self.style.WARNING(
                "No service/country pairs matched your filters — nothing to do."
            ))
            return

        # Build the resume-skip set (pairs already fresh)
        fresh = set()
        if options["resume"]:
            cutoff = timezone.now() - timedelta(hours=options["max_age"])
            fresh = set(
                Pricing.objects.filter(
                    country__server="server1",
                    service__server="server1",
                    updated_at__gte=cutoff,
                ).values_list("service_id", "country_id")
            )
            self.stdout.write(f"Resume mode: {len(fresh)} pairs already fresh, skipping them.")

        self.stdout.write(f"Fetching {total} price pairs... (long run — progress every 100)")

        ok = fail = skipped = processed = 0

        try:
            for svc in qs_services:
                for ctry in qs_countries:
                    processed += 1

                    if (svc.id, ctry.id) in fresh:
                        skipped += 1
                        continue

                    # Retry transient provider errors (502s, timeouts, hangs)
                    p = None
                    for attempt in range(self.MAX_RETRIES):
                        try:
                            p = provider.get_price(svc.code, ctry.name)
                            break
                        except Exception:
                            if attempt < self.MAX_RETRIES - 1:
                                time.sleep(options["sleep"] * 4)  # backoff

                    if not p or not p.get("success"):
                        fail += 1
                        continue

                    try:
                        cost_ngn, sell_ngn = to_ngn(p["price_usd"], config)
                        Pricing.objects.update_or_create(
                            country=ctry,
                            service=svc,
                            defaults={
                                "provider_cost": cost_ngn,
                                "selling_price": sell_ngn,
                                "is_available": p.get("available", 0) > 0,
                                "status": "active",
                            },
                        )
                        ok += 1
                    except Exception:
                        fail += 1

                    if processed % 100 == 0:
                        elapsed = time.time() - started
                        eta = (elapsed / processed) * (total - processed)
                        self.stdout.write(
                            f"progress: {processed}/{total} "
                            f"({100 * processed / total:.1f}%) "
                            f"ok={ok} fail={fail} skipped={skipped} "
                            f"elapsed={elapsed / 60:.0f}m eta={eta / 60:.0f}m"
                        )

                    time.sleep(options["sleep"])

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING(
                f"\nInterrupted at {processed}/{total}. "
                f"Rerun with --resume to continue where you left off."
            ))
            return
        
        self.stdout.write(self.style.SUCCESS(
            f"Prices synced: {ok} ok, {fail} failed, {skipped} skipped "
            f"(total time: {(time.time() - started) / 60:.0f} min)"
        ))