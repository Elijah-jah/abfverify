from django.core.management.base import BaseCommand

from countries.models import Country
from orders.models import Order
from pricing.models import Pricing
from services.models import Service


class Command(BaseCommand):
    help = ("Remove InstantNums (server1) countries, services and pricing. "
            "Rows referenced by orders are kept so order history survives.")

    def handle(self, *args, **options):
        # 1. Pricing rows for server1 — safe to wipe, nothing else references them
        deleted = Pricing.objects.filter(service__server="server1").delete()
        self.stdout.write(f"Pricing rows deleted: {deleted[0]}")

        # 2. Services — keep any that old orders point at
        used_services = set(
            Order.objects.filter(service__server="server1")
            .values_list("service_id", flat=True)
        )
        stale = Service.objects.filter(server="server1").exclude(id__in=used_services)
        n = stale.count()
        stale.delete()
        self.stdout.write(
            f"Services deleted: {n} | kept: {len(used_services)} (referenced by orders)"
        )

        # 3. Countries — keep any that old orders point at
        used_countries = set(
            Order.objects.filter(country__server="server1")
            .values_list("country_id", flat=True)
        )
        stale_c = Country.objects.filter(server="server1").exclude(id__in=used_countries)
        n = stale_c.count()
        stale_c.delete()
        self.stdout.write(
            f"Countries deleted: {n} | kept: {len(used_countries)} (referenced by orders)"
        )

        self.stdout.write(self.style.SUCCESS(
            "Cleanup done. Now run: python manage.py sync_smsbower"
        ))