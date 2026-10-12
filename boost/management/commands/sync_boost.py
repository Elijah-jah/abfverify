from django.core.management.base import BaseCommand

from boost.models import BoostService
from boost.providers import ReallySimpleSocial, ReallySimpleSocialError


class Command(BaseCommand):
    help = "Sync boost services from ReallySimpleSocial into the database"

    def handle(self, *args, **options):
        try:
            provider = ReallySimpleSocial()
            services = provider.get_services()
        except ReallySimpleSocialError as e:
            self.stderr.write(self.style.ERROR(f"Sync failed: {e}"))
            return

        created = updated = 0
        for s in services:
            defaults = {
                "name": s["name"],
                "category": s.get("category", ""),
                "service_type": s.get("type", ""),
                "rate": s["rate"],
                "min_order": s["min"],
                "max_order": s["max"],
                "refill": bool(s.get("refill")),
                "cancel": bool(s.get("cancel")),
            }
            desc = s.get("description") or s.get("desc")
            if desc:
                defaults["description"] = desc

            _, was_created = BoostService.objects.update_or_create(
                service_id=s["service"],
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Sync complete: {created} new, {updated} updated. Total received: {len(services)}"
        ))