from django.core.management.base import BaseCommand
from django.db.models import Count

from boost.models import BoostService
from boost.providers import ReallySimpleSocial, ReallySimpleSocialError


class Command(BaseCommand):
    help = (
        "Switch to ReallySimpleSocial: delete old services with no orders, "
        "deactivate old ones with orders, then import the FULL new catalog "
        "(name, category, type, rate, min/max, refill, cancel)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show what WOULD happen - change nothing",
        )

    def handle(self, *args, **opts):
        dry = opts["dry_run"]

        # ---- 1. Fetch the full catalog from the new provider ----
        try:
            api_services = ReallySimpleSocial().get_services()
        except ReallySimpleSocialError as e:
            self.stdout.write(self.style.ERROR(f"Provider error: {e}"))
            return

        if not isinstance(api_services, list) or not api_services:
            self.stdout.write(self.style.ERROR("Provider returned no services - aborting."))
            return

        provider_ids = {int(s["service"]) for s in api_services}
        self.stdout.write(f"Provider returned {len(provider_ids)} services")

        # ---- 2. Check for ID collisions with old rows that have orders ----
        collisions = (
            BoostService.objects
            .filter(service_id__in=provider_ids)
            .annotate(order_count=Count("orders"))
            .filter(order_count__gt=0)
        )
        if collisions.exists():
            self.stdout.write(self.style.WARNING(
                f"\n{collisions.count()} new service IDs collide with old rows that have "
                "order history. Those rows will be overwritten - orders stay safe, but "
                "the service NAME shown on old orders will change:"
            ))
            for c in collisions[:20]:
                self.stdout.write(f"  [{c.service_id}] {c.name} ({c.order_count} orders)")

        # ---- 3. Remove the old catalog ----
        old_services = BoostService.objects.exclude(service_id__in=provider_ids)
        old_with_orders = old_services.annotate(order_count=Count("orders")).filter(order_count__gt=0)
        old_without_orders = old_services.annotate(order_count=Count("orders")).filter(order_count=0)

        n_delete = old_without_orders.count()
        n_deactivate = old_with_orders.count()
        self.stdout.write(
            f"\nOld catalog: {n_delete} to DELETE (no orders), "
            f"{n_deactivate} to DEACTIVATE (has orders)"
        )

        if dry:
            self.stdout.write(self.style.SUCCESS("\nDRY-RUN complete - nothing changed."))
            return

        old_without_orders.delete()
        old_with_orders.update(is_active=False)

        # ---- 4. Import / update the full new catalog ----
        created = updated = 0
        for s in api_services:
            defaults = {
                "name": s["name"],
                "category": s.get("category", ""),
                "service_type": s.get("type", ""),
                "rate": s.get("rate", 0),
                "min_order": s.get("min", 1),
                "max_order": s.get("max", 1000),
                "refill": bool(s.get("refill")),
                "cancel": bool(s.get("cancel")),
                "is_active": True,
            }
            desc = s.get("description") or s.get("desc")
            if desc:
                defaults["description"] = desc

            _, was_created = BoostService.objects.update_or_create(
                service_id=int(s["service"]),
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        # ---- 5. Category summary ----
        cats = {}
        for s in api_services:
            cat = s.get("category") or "(no category)"
            cats[cat] = cats.get(cat, 0) + 1

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("CATEGORIES IMPORTED")
        self.stdout.write("=" * 60)
        for cat, count in sorted(cats.items()):
            self.stdout.write(f"  {cat[:45]:<47} {count:>4} services")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {created} created, {updated} updated, "
            f"{n_delete} old deleted, {n_deactivate} old deactivated. "
            f"Active services: {BoostService.objects.filter(is_active=True).count()}"
        ))