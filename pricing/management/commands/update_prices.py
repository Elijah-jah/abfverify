import time

from django.core.management.base import BaseCommand

from countries.models import Country
from services.models import Service
from pricing.models import Pricing
from pricing.services import PricingService
from providers.factory import get_provider
from providers.pvapins import PVAPinsProvider


class Command(BaseCommand):
    help = "Update all prices from providers (server3 uses PVAPins bulk rates)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            type=str,
            help="Only update this country name, e.g. --country USA",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without writing",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]

        self._update_server2()
        self._update_server3(country_filter=options["country"])

        self.stdout.write(self.style.SUCCESS("Price update complete!"))

    # ==================== server2 (unchanged) ====================

    def _update_server2(self):
        server = "server2"

        try:
            provider = get_provider(server=server)
        except ValueError:
            return

        countries = Country.objects.filter(status="active", server=server)
        services = Service.objects.filter(status="active", server=server)

        for country in countries:
            for service in services:
                try:
                    PricingService.update_price(
                        country=country,
                        service=service,
                        server=server,
                    )
                    self.stdout.write(self.style.SUCCESS(
                        "Updated: " + server + " | " + country.name + " | " + service.name
                    ))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        "Failed: " + server + " | " + country.name + " | " + service.name + " | " + str(e)
                    ))

    # ==================== server3 (PVAPins bulk) ====================

    def _update_server3(self, country_filter=None):
        server = "server3"
        provider = PVAPinsProvider()

        countries = Country.objects.filter(status="active", server=server)
        if country_filter:
            countries = countries.filter(name__iexact=country_filter)

        # Map of active services by lowercase name for fast matching
        active_services = {
            s.name.strip().lower(): s
            for s in Service.objects.filter(status="active", server=server)
        }

        for country in countries:
            try:
                # ONE provider call for the whole country
                rates = provider.get_rates(country.name)
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Rates failed: {country.name} | {e}"
                ))
                continue

            matched = 0
            unmatched_ids = []

            for name_lower, service in active_services.items():
                if name_lower in rates:
                    if not self.dry_run:
                        PricingService.update_price_from_rate(
                            country=country,
                            service=service,
                            price_usd=rates[name_lower],
                            server=server,
                        )
                    matched += 1
                else:
                    unmatched_ids.append(service.id)

            # One bulk write marks everything not in the rates as unavailable
            if unmatched_ids and not self.dry_run:
                Pricing.objects.filter(
                    country=country,
                    service_id__in=unmatched_ids,
                ).update(is_available=False)

            self.stdout.write(
                f"{country.name}: {matched}/{len(active_services)} services priced"
            )

            # Stay well under the 60/min rate limit
            time.sleep(1)
            