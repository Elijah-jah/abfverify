import re

from django.core.management.base import BaseCommand
from django.db.models import Count

from boost.models import BoostService, BoostOrder
from boost.providers import ReallySimpleSocial, ReallySimpleSocialError


TIMEFRAME_PATTERNS = [
    (re.compile(r"(\d+)\s*(?:days?|d(?![a-z]))", re.I), "days"),
    (re.compile(r"(\d+)\s*(?:hours?|hrs?)", re.I), "hours"),
    (re.compile(r"(\d+)\s*(?:minutes?|mins?)", re.I), "minutes"),
]
LONG_WORDS = re.compile(r"lifetime|permanent|non.?drop|never drop|365", re.I)


def detect_timeframe(name):
    """Returns (label, days_equivalent or None)."""
    for pattern, unit in TIMEFRAME_PATTERNS:
        m = pattern.search(name)
        if m:
            n = int(m.group(1))
            if unit == "days":
                return (f"{n} days", n)
            if unit == "hours":
                return (f"{n} hours", 0.5)   # treat hours as short
            return (f"{n} min", 0.1)
    if LONG_WORDS.search(name):
        return ("lifetime/permanent", 9999)
    return ("not stated", None)


class Command(BaseCommand):
    help = "Audit boost services: timeframe breakdown, order history, excess rows. Deletes nothing."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30,
                            help="Cutoff: services above this many days count as LONG")

    def handle(self, *args, **opts):
        cutoff = opts["days"]

        # ---- 1. What does the provider currently offer? ----
        provider_ids = set()
        try:
            api_services = ReallySimpleSocial().get_services()
            provider_ids = {str(s["service"]) for s in api_services}
            self.stdout.write(self.style.SUCCESS(
                f"Provider (ReallySimpleSocial) currently offers: {len(provider_ids)} services"
            ))
        except ReallySimpleSocialError as e:
            self.stdout.write(self.style.ERROR(f"Could not reach provider: {e}"))

        # ---- 2. Local DB state ----
        services = (
            BoostService.objects
            .annotate(order_count=Count("orders"))
            .order_by("category", "name")
        )
        total = services.count()
        self.stdout.write(f"Services in YOUR database: {total}")
        self.stdout.write("")

        # ---- 3. Classify each service ----
        buckets = {"short": [], "long": [], "unknown": []}
        excess = []
        cats = {}

        for s in services:
            label, days = detect_timeframe(s.name)
            in_provider = str(s.service_id) in provider_ids if provider_ids else None

            if not in_provider:
                excess.append((s, label, in_provider))

            if days is None:
                bucket = "unknown"
            elif days > cutoff:
                bucket = "long"
            else:
                bucket = "short"
            buckets[bucket].append((s, label, in_provider))

            c = cats.setdefault(s.category or "(no category)", {
                "total": 0, "short": 0, "long": 0, "unknown": 0, "orders": 0})
            c["total"] += 1
            c[bucket] += 1
            c["orders"] += s.order_count

        # ---- 4. Summary by category ----
        self.stdout.write("=" * 78)
        self.stdout.write(f"CATEGORY BREAKDOWN  (short = up to {cutoff} days)")
        self.stdout.write("=" * 78)
        self.stdout.write(f'{"Category":<34}{"Svcs":>6}{"Short":>7}{"Long":>6}{"??":>5}{"Orders":>8}')
        self.stdout.write("-" * 78)
        for cat, c in sorted(cats.items()):
            self.stdout.write(
                f'{cat[:33]:<34}{c["total"]:>6}{c["short"]:>7}{c["long"]:>6}{c["unknown"]:>5}{c["orders"]:>8}'
            )
        self.stdout.write("")

        # ---- 5. The kill lists (what we'd delete/deactivate) ----
        def report(title, rows, color):
            self.stdout.write("=" * 78)
            self.stdout.write(f"{title}: {len(rows)}")
            self.stdout.write("=" * 78)
            for s, label, in_provider in rows:
                tag = "HAS ORDERS - deactivate only" if s.order_count else "safe to DELETE"
                self.stdout.write(
                    f"[{s.service_id}] {s.name[:44]:<46} {label:<16} {tag}"
                )
            self.stdout.write("")

        report(f"LONG timeframe (> {cutoff} days) - delete candidates", buckets["long"], "ERROR")
        report("Excess (in your DB but provider no longer offers)", excess, "WARNING")

        # ---- 6. Totals ----
        self.stdout.write("=" * 78)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 78)
        self.stdout.write(f"Short (keep)      : {len(buckets['short'])}")
        self.stdout.write(f"Long (kill)       : {len(buckets['long'])}")
        self.stdout.write(f"Unknown (decide)  : {len(buckets['unknown'])}")
        self.stdout.write(f"Excess (kill)     : {len(excess)}")
        self.stdout.write(f"Services w/ orders: {sum(1 for s in services if s.order_count)}")
        self.stdout.write(f"Total boost orders: {BoostOrder.objects.count()}")
