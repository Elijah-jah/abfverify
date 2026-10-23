from django.core.management.base import BaseCommand

from countries.models import Country
from services.models import Service
from pricing.models import Pricing
from orders.models import Order


class Command(BaseCommand):
    help = "Retire server3: merge order history into server1 (inactive), delete the rest."

    def handle(self, *args, **options):
        # ---- 1. PRICING: no orders reference it - delete outright ----
        p_count = Pricing.objects.filter(country__server="server3").count()
        Pricing.objects.filter(country__server="server3").delete()
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {p_count} server3 pricing rows"
        ))

        # ---- 2. SERVICES WITH ORDER HISTORY: keep, relabel as inactive server1 ----
        kept_services = Service.objects.filter(
            server="server3", orders__isnull=False
        ).distinct()
        kept_ids = list(kept_services.values_list("id", flat=True))
        updated = kept_services.update(server="server1", status="inactive")
        self.stdout.write(self.style.WARNING(
            f"Merged {updated} server3 services (have orders) -> server1, set inactive"
        ))

        # ---- 3. SERVICES WITHOUT ORDERS: delete ----
        remaining = Service.objects.filter(server="server3").exclude(id__in=kept_ids)
        s_count = remaining.count()
        remaining.delete()
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {s_count} server3 services (no orders)"
        ))

        # ---- 4. COUNTRIES: orders link to services, not countries - safe to delete ----
        try:
            c_count = Country.objects.filter(server="server3").count()
            Country.objects.filter(server="server3").delete()
            self.stdout.write(self.style.SUCCESS(
                f"Deleted {c_count} server3 countries"
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"Country delete failed (FK protection?) - services/pricing are clean. Error: {e}"
            ))

        # ---- FINAL SUMMARY ----
        from collections import Counter
        self.stdout.write("----------------------------------------")
        self.stdout.write(f"Countries now : {dict(Counter(Country.objects.values_list('server', flat=True)))}")
        self.stdout.write(f"Services now  : {dict(Counter(Service.objects.values_list('server', flat=True)))}")
        self.stdout.write(f"Pricing now   : {dict(Counter(Pricing.objects.values_list('country__server', flat=True)))}")
        self.stdout.write(f"Orders intact : {Order.objects.count()}")
        self.stdout.write(self.style.SUCCESS("Done."))
