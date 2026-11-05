from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from boost.models import BoostService
from boost.providers import ReallySimpleSocial, ReallySimpleSocialError


TARGET_NAME = "Tiktok followers | No refill - NGN 5000 per 1000"
TARGET_RATE = Decimal("5000")
TARGET_CATEGORY = "TikTok"


def normalize_name(value):
    return " ".join(str(value or "").split()).casefold()


def get_rate(service):
    try:
        return Decimal(str(service.get("rate", "0")))
    except (InvalidOperation, TypeError, ValueError):
        return None


class Command(BaseCommand):
    help = "Import the selected TikTok followers service from ReallySimpleSocial."

    def handle(self, *args, **options):
        try:
            services = ReallySimpleSocial().get_services()
        except ReallySimpleSocialError as exc:
            raise CommandError(f"Provider connection failed: {exc}") from exc

        # First try an exact name match.
        matches = [
            service
            for service in services
            if normalize_name(service.get("name")) == normalize_name(TARGET_NAME)
            and get_rate(service) == TARGET_RATE
        ]

        # Fallback in case the provider slightly changes the name formatting.
        if not matches:
            matches = [
                service
                for service in services
                if "tiktok" in normalize_name(service.get("name"))
                and "follower" in normalize_name(service.get("name"))
                and "no refill" in normalize_name(service.get("name"))
                and get_rate(service) == TARGET_RATE
            ]

        if not matches:
            self.stdout.write(
                self.style.WARNING(
                    "The requested service was not found. Available TikTok follower services:"
                )
            )

            available = [
                service
                for service in services
                if "tiktok" in normalize_name(service.get("name"))
                and "follower" in normalize_name(service.get("name"))
            ]

            for service in available[:30]:
                self.stdout.write(
                    f"[{service.get('service')}] {service.get('name')} "
                    f"(rate: {service.get('rate')})"
                )

            raise CommandError("No matching TikTok followers service was imported.")

        if len(matches) > 1:
            for service in matches:
                self.stdout.write(
                    f"[{service.get('service')}] {service.get('name')} "
                    f"(rate: {service.get('rate')})"
                )
            raise CommandError(
                "Multiple services matched. No service was imported automatically."
            )

        service = matches[0]

        defaults = {
            "name": service["name"],
            "category": TARGET_CATEGORY,
            "service_type": service.get("type", ""),
            "rate": get_rate(service),
            "min_order": service.get("min", 1),
            "max_order": service.get("max", 1000),
            "refill": False,
            "cancel": bool(service.get("cancel")),
            "is_active": True,
        }

        description = service.get("description") or service.get("desc")
        if description:
            defaults["description"] = description

        obj, created = BoostService.objects.update_or_create(
            service_id=int(service["service"]),
            defaults=defaults,
        )

        action = "Imported" if created else "Updated and activated"

        self.stdout.write(
            self.style.SUCCESS(
                f"{action}: [{obj.service_id}] {obj.name}\n"
                f"Category: {obj.category}\n"
                f"Provider rate: NGN {obj.rate} per 1000\n"
                f"Quantity: {obj.min_order:,}–{obj.max_order:,}\n"
                f"Refill: No"
            )
        )