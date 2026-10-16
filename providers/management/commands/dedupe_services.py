
from django.core.management.base import BaseCommand
from django.db.models import Count

from services.models import Service
from pricing.models import Pricing


class Command(BaseCommand):
    help = "Remove duplicate server1 services (same code), merging prices onto the canonical row."

    def handle(self, *args, **options):
        dupes = (
            Service.objects.filter(server="server1")
            .values("code")
            .annotate(n=Count("id"))
            .filter(n__gt=1)
        )
        removed = 0
        for d in dupes:
            code = d["code"]
            rows = list(
                Service.objects.filter(server="server1", code=code)
                .order_by("-provider_id")
            )
            keep = rows[0]
            for extra in rows[1:]:
                Pricing.objects.filter(service=extra).update(service=keep)
                extra.delete()
                removed += 1
            self.stdout.write(self.style.SUCCESS(f"deduped: {code}"))

        self.stdout.write(self.style.SUCCESS(f"done - removed {removed} duplicate rows"))

        # Show coverage of your main sellers
        for code in ["WhatsApp", "WhatsApp (USA Physical SIM)", "Telegram", "Google/Gmail"]:
            n = Pricing.objects.filter(service__server="server1", service__code=code).count()
            self.stdout.write(f"{code}: {n}/151")