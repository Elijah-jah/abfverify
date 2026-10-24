from django.core.management.base import BaseCommand

from boost.models import BoostService
from boost.providers import ReallySimpleSocial, ReallySimpleSocialError


NEW_SERVICE_ID = 9819  # Facebook Page Followers | Non Drop @ 200


class Command(BaseCommand):
    help = "Swap Facebook Page Followers: remove current ones, add the 9819 (rate 200) variant."

    def handle(self, *args, **options):
        try:
            api = {str(s["service"]): s for s in ReallySimpleSocial().get_services()}
        except ReallySimpleSocialError as e:
            self.stdout.write(self.style.ERROR(f"Provider unreachable: {e}"))
            return

        if str(NEW_SERVICE_ID) not in api:
            self.stdout.write(self.style.ERROR(f"Service {NEW_SERVICE_ID} not found at provider."))
            return

        s = api[str(NEW_SERVICE_ID)]

        # ---- 1. Remove every other Facebook Page Followers service ----
        fb_qs = BoostService.objects.filter(
            name__icontains="facebook page followers"
        ).exclude(service_id=NEW_SERVICE_ID)

        for svc in fb_qs:
            n_orders = svc.orders.count()
            if n_orders:
                svc.is_active = False
                svc.save(update_fields=["is_active"])
                self.stdout.write(self.style.WARNING(
                    f"Deactivated [{svc.service_id}] {svc.name} ({n_orders} orders preserved)"
                ))
            else:
                self.stdout.write(f"Deleted [{svc.service_id}] {svc.name}")
                svc.delete()

        # ---- 2. Create/activate the 9819 variant ----
        new, created = BoostService.objects.update_or_create(
            service_id=NEW_SERVICE_ID,
            defaults={
                "name": s["name"],
                "category": s.get("category", ""),
                "service_type": s.get("type", ""),
                "rate": s["rate"],
                "min_order": s.get("min", 1),
                "max_order": s.get("max", 1000),
                "refill": bool(s.get("refill")),
                "cancel": bool(s.get("cancel")),
                "is_active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Activated'}: [{new.service_id}] {new.name} (rate {new.rate})"
        ))

        # ---- 3. Verify ----
        active_fb = BoostService.objects.filter(
            name__icontains="facebook page followers", is_active=True
        )
        self.stdout.write("Active Facebook Page Followers services now:")
        for svc in active_fb:
            self.stdout.write(f"  [{svc.service_id}] {svc.name} (rate {svc.rate})")
        self.stdout.write(self.style.SUCCESS("Done."))
