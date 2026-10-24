import re

from django.core.management.base import BaseCommand
from django.db.models import Count

from boost.models import BoostService
from boost.providers import ReallySimpleSocial, ReallySimpleSocialError


TIMEFRAME_PATTERNS = [
    (re.compile(r"(\d+)\s*(?:days?|d(?![a-z]))", re.I), "days"),
    (re.compile(r"(\d+)\s*(?:hours?|hrs?)", re.I), "hours"),
    (re.compile(r"(\d+)\s*(?:minutes?|mins?)", re.I), "minutes"),
]
LONG_WORDS = re.compile(r"lifetime|permanent|non.?drop|never drop|365", re.I)


def detect_timeframe(name):
    for pattern, unit in TIMEFRAME_PATTERNS:
        m = pattern.search(name)
        if m:
            n = int(m.group(1))
            if unit == "days":
                return n
            return 0.5
    if LONG_WORDS.search(name):
        return 9999
    return None


class Command(BaseCommand):
    help = "Clean boost services: delete long-timeframe + excess (deactivate if they have orders)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30,
                            help="Long = more than this many days (default 30)")
        parser.add_argument("--unknown", choices=["keep", "delete"], default="keep",
                            help="What to do with services that state no timeframe (default keep)")
        parser.add_argument("--dry-run", action="store_true",
                            help="Show what WOULD happen - change nothing")

    def handle(self, *args, **opts):
        cutoff = opts["days"]
        dry = opts["dry_run"]

        # What does the provider currently offer?
        provider_ids = set()
        try:
            api = ReallySimpleSocial().get_services()
            provider_ids = {str(s["service"]) for s in api}
            self.stdout.write(f"Provider offers: {len(provider_ids)} services")
        except ReallySimpleSocialError as e:
            self.stdout.write(self.style.WARNING(f"Provider unreachable - excess check skipped: {e}"))

        services = BoostService.objects.annotate(order_count=Count("orders"))
        total = services.count()

        plan_delete, plan_deactivate, plan_keep = [], [], []

        for s in services:
            days = detect_timeframe(s.name)
            is_long = days is not None and days > cutoff
            is_excess = bool(provider_ids) and str(s.service_id) not in provider_ids

            if is_long or is_excess:
                if s.order_count:
                    plan_deactivate.append((s, "long" if is_long else "excess"))
                else:
                    plan_delete.append((s, "long" if is_long else "excess"))
            elif days is None and opts["unknown"] == "delete":
                if s.order_count:
                    plan_deactivate.append((s, "unknown"))
                else:
                    plan_delete.append((s, "unknown"))
            else:
                plan_keep.append(s)

        mode = "DRY-RUN (nothing changed)" if dry else "APPLYING"
        self.stdout.write(self.style.WARNING(f"--- {mode} ---"))
        self.stdout.write(f"Keep              : {len(plan_keep)}")
        self.stdout.write(f"DELETE (no orders): {len(plan_delete)}")
        self.stdout.write(f"DEACTIVATE (orders): {len(plan_deactivate)}")
        self.stdout.write("")

        for s, why in plan_deactivate:
            self.stdout.write(f"  DEACTIVATE [{s.service_id}] {s.name} ({why}, {s.order_count} orders)")
        for s, why in plan_delete[:40]:
            self.stdout.write(f"  DELETE     [{s.service_id}] {s.name} ({why})")
        if len(plan_delete) > 40:
            self.stdout.write(f"  ... and {len(plan_delete) - 40} more")

        if dry:
            self.stdout.write(self.style.SUCCESS("Dry-run complete - rerun without --dry-run to apply."))
            return

        for s, _ in plan_deactivate:
            s.is_active = False
            s.save(update_fields=["is_active"])
        delete_ids = [s.id for s, _ in plan_delete]
        deleted = BoostService.objects.filter(id__in=delete_ids).delete()

        self.stdout.write(self.style.SUCCESS(
            f"Done. Deleted {deleted[0]} rows, deactivated {len(plan_deactivate)}. "
            f"Remaining services: {BoostService.objects.count()}"
        ))
