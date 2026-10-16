import time

from django.core.management.base import BaseCommand

from countries.models import Country
from services.models import Service
from pricing.services import PricingService
from providers.factory import get_provider


class Command(BaseCommand):
    help = "Update all prices from providers and save to database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without writing",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]

        self._update_server1()
        self._update_server2()

        self.stdout.write(self.style.SUCCESS("Price update complete!"))

    # ==================== server1 (InstantNums — no bulk endpoint) ====================

    def _update_server1(self):
        server = "server1"

        try:
            provider = get_provider(server=server)
        except ValueError:
            self.stdout.write(self.style.WARNING("No provider configured for server1"))
            return

        try:
            # Probe: InstantNums currently has no bulk price endpoint (400 without service param)
            provider.get_all_prices("United States")
        except Exception:
            self.stdout.write(self.style.WARNING(
                "InstantNums: no bulk endpoint. Refresh prices with "
                "sync_instantnums --services \"WhatsApp,Telegram,...\" --sleep 5 --resume "
                "(and recalc_prices after a profit change)"
            ))
            return

    # ==================== server2 (DaisySMS bulk) ====================

    def _update_server2(self):
        server = "server2"

        try:
            provider = get_provider(server=server)
        except ValueError:
            self.stdout.write(self.style.WARNING("No provider configured for server2"))
            return

        try:
            rates = provider.get_all_prices(187)  # USA
        except PermissionError as e:
            self.stdout.write(self.style.ERROR(f"DaisySMS auth failed: {e}"))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"DaisySMS price fetch failed: {e}"))
            return

        rates_by_code = {
            code.strip().lower(): info.get("cost", 0)
            for code, info in rates.items()
            if info.get("cost")
        }

        active_services = {
            s.code.strip().lower(): s
            for s in Service.objects.filter(status="active", server=server)
            if s.code
        }

        countries = Country.objects.filter(status="active", server=server)

        for country in countries:
            matched = 0
            unmatched = []

            for code_lower, service in active_services.items():
                if code_lower in rates_by_code:
                    if not self.dry_run:
                        PricingService.update_price_from_rate(
                            country=country,
                            service=service,
                            price_usd=str(rates_by_code[code_lower]),
                            server=server,
                        )
                    matched += 1
                else:
                    unmatched.append(service.code)

            self.stdout.write(
                f"{country.name}: {matched}/{len(active_services)} services priced"
            )

            if unmatched:
                self.stdout.write(self.style.WARNING(
                    f"  not in Daisy rates: {', '.join(unmatched[:10])}"
                    + (" ..." if len(unmatched) > 10 else "")
                ))