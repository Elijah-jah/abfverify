from django.core.management.base import BaseCommand
from countries.models import Country
from services.models import Service
from pricing.services import PricingService


class Command(BaseCommand):
    help = "Update all pricing from provider APIs (server2 & server3)"

    def handle(self, *args, **kwargs):
        active_servers = ["server2", "server3"]
        total_updated = 0
        total_failed = 0

        for server in active_servers:
            self.stdout.write(f"\n>>> Processing {server}...")

            countries = Country.objects.filter(status="active", server=server)
            services = Service.objects.filter(status="active", server=server)

            server_count = 0

            for country in countries:
                for service in services:
                    try:
                        PricingService.update_price(
                            country=country,
                            service=service,
                            server=server,
                        )
                        server_count += 1
                        total_updated += 1

                    except Exception as e:
                        total_failed += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ✗ {country.name} / {service.name}: {e}"
                            )
                        )

            self.stdout.write(
                self.style.SUCCESS(f"  ✓ {server}: {server_count} updated")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'='*50}"
                f"\nDONE: {total_updated} updated, {total_failed} failed"
                f"\n{'='*50}"
            )
        )