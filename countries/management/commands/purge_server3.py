from django.core.management.base import BaseCommand

from countries.models import Country
from services.models import Service
from pricing.models import Pricing
from orders.models import Order


class Command(BaseCommand):
    help = "Delete all leftover server3 countries, services and pricing rows."

    def handle(self, *args, **options):
        # ---- SAFETY CHECK: never delete data that order history depends on ----
        orders_on_services = Order.objects.filter(service__server="server3").count()
        orders_provider = Order.objects.filter(provider="server3").count()

        self.stdout.write(f"Orders referencing server3 services : {orders_on_services}")
        self.stdout.write(f"Orders with provider='server3'     : {orders_provider}")

        if orders_on_services or orders_provider:
            self.stdout.write(self.style.ERROR(
                "ABORTED - server3 still has order history. Nothing was deleted."
            ))
            return

        # ---- PURGE (order matters: pricing -> services -> countries) ----
        plan = [
            ("pricing rows", Pricing.objects.filter(country__server="server3")),
            ("services",     Service.objects.filter(server="server3")),
            ("countries",    Country.objects.filter(server="server3")),
        ]

        for label, qs in plan:
            count = qs.count()
            if count:
                qs.delete()
                self.stdout.write(self.style.SUCCESS(f"Deleted {count} server3 {label}"))
            else:
                self.stdout.write(f"No server3 {label} found - skipped")

        # ---- FINAL SUMMARY ----
        def counts(model, field="server"):
            from collections import Counter
            return dict(Counter(model.objects.values_list(field, flat=True)))

        self.stdout.write("----------------------------------------")
        self.stdout.write(f"Countries now : {counts(Country)}")
        self.stdout.write(f"Services now  : {counts(Service)}")
        self.stdout.write(f"Pricing now   : {counts(Pricing, 'country__server')}")
        self.stdout.write(self.style.SUCCESS("Done."))
