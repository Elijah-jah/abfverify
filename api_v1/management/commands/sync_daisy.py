from django.core.management.base import BaseCommand
from django.utils import timezone

from countries.models import Country
from services.models import Service
from pricing.models import Pricing
from pricing.services import PricingService
from providers.factory import get_provider


class Command(BaseCommand):
    help = "Sync DaisySMS prices + stock into the Pricing table (server2, USA=187)"

    def handle(self, *args, **options):
        provider = get_provider(server="server2")
        usa = Country.objects.filter(server="server2").first()
        if not usa:
            self.stdout.write(self.style.ERROR("No country found for server2"))
            return

        services = Service.objects.filter(server="server2", status="active")
        ok = fail = 0

        for s in services:
            try:
                # Price — PricingService applies your margin automatically
                PricingService.update_price(country=usa, service=s, server="server2")

                # Stock — save into is_available
                result = provider.check_stock(service=s.code, country=187)
                available = result.get("available", 0)
                Pricing.objects.filter(country=usa, service=s).update(
                    is_available=available > 0,
                    updated_at=timezone.now(),
                )

                ok += 1
                self.stdout.write(f"OK   {s.code:<22} stock={available}")
            except Exception as e:
                fail += 1
                self.stdout.write(f"FAIL {s.code}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Done. {ok} updated, {fail} failed."))