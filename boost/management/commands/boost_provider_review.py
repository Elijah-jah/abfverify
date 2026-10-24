import json
import re
from collections import defaultdict

from django.core.management.base import BaseCommand

from boost.providers import ReallySimpleSocial, ReallySimpleSocialError


def tf_summary(s):
    """Pull any timeframe-ish fields out of a raw service dict."""
    parts = []
    for k, v in s.items():
        if re.search(r"day|durat|drip|speed|refill|guarantee", str(k), re.I):
            parts.append(f"{k}={v}")
    return " | ".join(parts) if parts else "-"


class Command(BaseCommand):
    help = "Dump the full provider catalog with timeframe fields for review."

    def handle(self, *args, **opts):
        try:
            services = ReallySimpleSocial().get_services()
        except ReallySimpleSocialError as e:
            self.stdout.write(self.style.ERROR(f"Provider error: {e}"))
            return

        self.stdout.write(f"TOTAL SERVICES FROM PROVIDER: {len(services)}")

        # What fields exist across ALL services?
        keys = set()
        for s in services:
            keys.update(s.keys())
        self.stdout.write(f"ALL FIELDS: {sorted(keys)}")

        # Save the full raw dump for reference
        with open("provider_services.json", "w") as f:
            json.dump(services, f, indent=1)
        self.stdout.write("Full raw dump saved to provider_services.json")

        # One sample service, full JSON
        self.stdout.write("SAMPLE SERVICE:")
        self.stdout.write(json.dumps(services[0], indent=2))

        # Compact review table grouped by category
        self.stdout.write("")
        self.stdout.write("=" * 100)
        self.stdout.write("FULL CATALOG (grouped by category)")
        self.stdout.write("=" * 100)
        by_cat = defaultdict(list)
        for s in services:
            by_cat[s.get("category", "(none)")].append(s)

        for cat in sorted(by_cat):
            rows = by_cat[cat]
            self.stdout.write(f"\n### {cat} ({len(rows)})")
            for s in sorted(rows, key=lambda x: x.get("rate", 0)):
                self.stdout.write(
                    f"[{s['service']}] {s['name'][:52]:<54} "
                    f"rate={s.get('rate')} min={s.get('min')} max={s.get('max')}  "
                    f"TF: {tf_summary(s)}"
                )
