from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import Count, ForeignKey

from countries.models import Country
from services.models import Service
from pricing.models import Pricing


def fk_pointing_to(model):
    """All (related_model, fk_field_name) pairs that reference `model`."""
    out = []
    for rel in model._meta.related_objects:
        f = rel.field
        if isinstance(f, ForeignKey) and f.remote_field.model is model and not f.unique:
            out.append((rel.related_model, f.name))
    return out


class Command(BaseCommand):
    help = "Remove duplicate server1 countries/services (keeps the original row, merges references)."

    def _dedupe(self, model, key_fields, restrict, label):
        related = fk_pointing_to(model)
        groups = (
            model.objects.filter(**restrict)
            .values(*key_fields)
            .annotate(n=Count("id"))
            .filter(n__gt=1)
        )

        deleted = 0
        moved = 0
        for g in groups:
            lookup = {k: g[k] for k in key_fields}
            members = list(model.objects.filter(**restrict, **lookup).order_by("id"))
            keeper = members[0]          # original (first created) survives
            for dup in members[1:]:        # merged copies get removed
                for rel_model, fk_name in related:
                    cnt = rel_model.objects.filter(**{fk_name: dup.pk}).update(**{fk_name: keeper.pk})
                    moved += cnt
                dup.delete()
                deleted += 1

        status = self.style.SUCCESS if deleted else self.style.WARNING
        self.stdout.write(status(f"{label}: {deleted} duplicate(s) removed, {moved} reference(s) moved to the original"))
        return deleted

    def handle(self, *args, **options):
        self.stdout.write("Scanning for duplicates (keeping the ORIGINAL lowest-ID row)...")
        self.stdout.write("----------------------------------------------------------")

        # 1. Countries: same name on server1 = duplicate
        self._dedupe(Country, ["name"], {"server": "server1"}, "Countries")

        # 2. Services: same name + provider_id on server1 = duplicate
        self._dedupe(Service, ["name", "provider_id"], {"server": "server1"}, "Services")

        # 3. Pricing: after the merges, same country+service pairs may now collide
        self._dedupe(Pricing, ["country", "service"], {}, "Pricing rows")

        self.stdout.write("----------------------------------------------------------")
        self.stdout.write(f"Countries now : {dict(Counter(Country.objects.values_list('server', flat=True)))}")
        self.stdout.write(f"Services now  : {dict(Counter(Service.objects.values_list('server', flat=True)))}")
        self.stdout.write(self.style.SUCCESS("Done."))
