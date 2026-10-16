from django.core.management.base import BaseCommand
from django.db.models import Count

from pricing.models import Pricing


class Command(BaseCommand):
    help = "Remove duplicate Pricing rows for the same service+country pair."

    def handle(self, *args, **options):
        dupes = (
            Pricing.objects.values("service_id", "country_id")
            .annotate(n=Count("id"))
            .filter(n__gt=1)
        )
        removed = 0
        for d in dupes:
            rows = list(
                Pricing.objects.filter(
                    service_id=d["service_id"],
                    country_id=d["country_id"],
                ).order_by("-updated_at", "id")
            )
            keep = rows[0]
            for extra in rows[1:]:
                extra.delete()
                removed += 1
        self.stdout.write(self.style.SUCCESS(f"done - removed {removed} duplicate pricing rows"))

        for code in ["WhatsApp", "WhatsApp (USA Physical SIM)", "Telegram", "Google/Gmail"]:
            n = Pricing.objects.filter(service__server="server1", service__code=code).count()
            self.stdout.write(f"{code}: {n}/151")