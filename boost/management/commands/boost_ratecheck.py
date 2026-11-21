from django.core.management.base import BaseCommand

from boost.models import BoostService
from boost.providers import ReallySimpleSocial


class Command(BaseCommand):
    help = "Debug: compare DB rate vs live API rate"

    def handle(self, *args, **opts):
        self.stdout.write("=== DATABASE ===")
        for s in BoostService.objects.filter(name__icontains="30 Days Refill"):
            self.stdout.write(f"DB  -> ID: {s.service_id}  RATE: {s.rate}  |  {s.name}")

        self.stdout.write("Fetching from API (takes a few seconds)...")
        try:
            services = ReallySimpleSocial().get_services()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"API error: {e}"))
            return

        self.stdout.write("=== API ===")
        for s in services:
            if "30 Days Refill" in s.get("name", "") and "Tiktok" in s.get("name", ""):
                self.stdout.write(f"API -> {s}")
