from django.core.management.base import BaseCommand
from django.db.models import Count

from countries.models import Country
from pricing.models import Pricing
from orders.models import Order


class Command(BaseCommand):
    help = "Remove duplicate server1 countries (same name), re-pointing prices and orders."

    def handle(self, *args, **options):
        total = Country.objects.filter(server="server1").count()
        self.stdout.write(f"server1 countries total: {total} (should be 151)")

        dupes = (
            Country.objects.filter(server="server1")
            .values("name")
            .annotate(n=Count("id"))
            .filter(n__gt=1)
        )
        removed = 0
        for d in dupes:
            rows = list(
                Country.objects.filter(server="server1", name=d["name"])
                .order_by("-provider_id", "id")
            )
            keep = rows[0]
            for extra in rows[1:]:
                Pricing.objects.filter(country=extra).update(country=keep)
                Order.objects.filter(country=extra).update(country=keep)
                extra.delete()
                removed += 1
            self.stdout.write(self.style.SUCCESS(f"deduped country: {d['name']}"))

        self.stdout.write(self.style.SUCCESS(f"done - removed {removed} duplicate countries"))

        for code in ["WhatsApp", "WhatsApp (USA Physical SIM)", "Telegram", "Google/Gmail"]:
            n = Pricing.objects.filter(service__server="server1", service__code=code).count()
            self.stdout.write(f"{code}: {n}/151")