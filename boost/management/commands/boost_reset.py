from django.core.management.base import BaseCommand

from boost.models import BoostService
from boost.providers import ReallySimpleSocial, ReallySimpleSocialError


def base_name(name):
    """'Telegram Views | Auto' -> 'telegram views' (used to find duplicates)."""
    n = name.split("|")[0].strip().lower()
    return n.removeprefix("new!").strip()


class Command(BaseCommand):
    help = ("Reset boost catalog: keep 1 Facebook Followers (Non Drop), 1 Instagram "
            "Followers, 1 per duplicate group - deactivate/delete everything else.")

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--keep-singletons", action="store_true",
                            help="Also keep services that have no duplicates")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        try:
            api = ReallySimpleSocial().get_services()
        except ReallySimpleSocialError as e:
            self.stdout.write(self.style.ERROR(f"Provider unreachable: {e}"))
            return

        def cheapest(match):
            cands = [s for s in api if match(s)]
            return min(cands, key=lambda s: float(s.get("rate") or 0)) if cands else None

        # ---- 1. The two explicit keeps ----
        fb = cheapest(lambda s: "facebook" in s["name"].lower()
                                and "follower" in s["name"].lower()
                                and "non drop" in s["name"].lower())
        ig = cheapest(lambda s: "instagram" in s["name"].lower()
                                and "follower" in s["name"].lower())

        # ---- 2. One per duplicate group ----
        groups = {}
        for s in api:
            groups.setdefault(base_name(s["name"]), []).append(s)

        keep_api = {}
        if fb:
            keep_api[str(fb["service"])] = fb
        if ig:
            keep_api[str(ig["service"])] = ig

        self.stdout.write("=" * 80)
        self.stdout.write("WILL KEEP (re-created in DB if missing):")
        self.stdout.write("=" * 80)
        if fb:
            self.stdout.write(f"  [FB]  [{fb['service']}] {fb['name']} (rate {fb.get('rate')})")
        if ig:
            self.stdout.write(f"  [IG]  [{ig['service']}] {ig['name']} (rate {ig.get('rate')})")

        for b, members in sorted(groups.items()):
            if len(members) >= 2:
                c = min(members, key=lambda s: float(s.get("rate") or 0))
                keep_api[str(c["service"])] = c
                self.stdout.write(f"  [DUP x{len(members)}] [{c['service']}] {c['name']} (rate {c.get('rate')})")
            elif opts["keep_singletons"]:
                keep_api[str(members[0]["service"])] = members[0]
                self.stdout.write(f"  [ONE]  [{members[0]['service']}] {members[0]['name']}")

        self.stdout.write(f"\nTotal kept: {len(keep_api)} services")

        # ---- 3. What happens to current DB rows ----
        keep_ids = [int(i) for i in keep_api]
        others = BoostService.objects.exclude(service_id__in=keep_ids)
        n_del = others.filter(orders__isnull=True).count()
        n_deact = others.filter(orders__isnull=False).distinct().count()
        self.stdout.write(f"Current DB rows to DELETE: {n_del}")
        self.stdout.write(f"Current DB rows to DEACTIVATE (has orders): {n_deact}")

        if dry:
            self.stdout.write(self.style.SUCCESS("\nDRY-RUN complete - nothing changed."))
            return

        # ---- 4. Apply: upsert keeps (reactivate if needed) ----
        for sid, s in keep_api.items():
            obj, created = BoostService.objects.update_or_create(
                service_id=int(sid),
                defaults={
                    "name": s["name"],
                    "category": s.get("category", ""),
                    "service_type": s.get("type", ""),
                    "rate": s.get("rate", 0),
                    "min_order": s.get("min", 1),
                    "max_order": s.get("max", 1000),
                    "refill": bool(s.get("refill")),
                    "cancel": bool(s.get("cancel")),
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(f"  + created [{sid}] {s['name']}")
            elif not obj.is_active:
                obj.is_active = True
                obj.save(update_fields=["is_active"])
                self.stdout.write(f"  ^ reactivated [{sid}] {s['name']}")

        # ---- 5. Apply: remove the rest ----
        for s in BoostService.objects.exclude(service_id__in=keep_ids):
            if s.orders.exists():
                s.is_active = False
                s.save(update_fields=["is_active"])
            else:
                s.delete()

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Catalog is now {len(keep_api)} services "
            f"({BoostService.objects.filter(is_active=True).count()} active in DB)."
        ))
