from django.core.management.base import BaseCommand

from pricing.models import Pricing


class Command(BaseCommand):
    help = "Delete price rows for server1 services that point at stale non-server1 countries."

    def handle(self, *args, **options):
        stale = (
            Pricing.objects
            .filter(service__server="server1")
            .exclude(country__server="server1")
        )
        n = stale.count()
        stale.delete()
        self.stdout.write(self.style.SUCCESS(f"deleted {n} stale price rows"))

        for code in ["WhatsApp", "WhatsApp (USA Physical SIM)", "Telegram", "Google/Gmail"]:
            cnt = Pricing.objects.filter(service__server="server1", service__code=code).count()
            self.stdout.write(f"{code}: {cnt}/151")