from django.core.management.base import BaseCommand

from countries.models import Country
from services.models import Service
from providers.pvapins import PVAPinsProvider


class Command(BaseCommand):
    help = "Sync countries and services from PVAPins into the local catalog (server3)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving to the database",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        server = "server3"

        provider = PVAPinsProvider()

        # ==================== COUNTRIES ====================

        pv_countries = provider.get_countries()["countries"]
        # shape: [{"id": "US", "full_name": "USA"}, ...]

        seen_names = []
        created = 0
        updated = 0

        for item in pv_countries:
            name = item["full_name"]
            iso = item["id"]
            seen_names.append(name.lower())

            # Prefer matching an existing row by iso_code, then by name
            obj = Country.objects.filter(server=server, iso_code=iso).first()

            if not obj:
                obj = Country.objects.filter(
                    server=server, name__iexact=name
                ).first()

            if obj:
                if not dry_run:
                    obj.name = name
                    obj.iso_code = iso
                    obj.status = "active"
                    obj.save()
                updated += 1
            else:
                if not dry_run:
                    Country.objects.create(
                        name=name,
                        iso_code=iso,
                        server=server,
                        status="active",
                    )
                created += 1

        # Deactivate server3 rows that no longer exist at PVAPins
        # (never delete — Orders reference these with PROTECT)
        deactivated = 0
        for c in Country.objects.filter(server=server):
            if c.name.lower() not in seen_names and c.status != "inactive":
                if not dry_run:
                    c.status = "inactive"
                    c.save()
                deactivated += 1

        self.stdout.write(
            f"Countries: {created} created, {updated} updated, {deactivated} deactivated"
        )

        # ==================== SERVICES ====================

        pv_services = provider.get_services()["services"]
        # shape: [{"code": "wa", "name": "Whatsapp"}, ...]

        seen_names = []
        created = 0
        updated = 0

        for item in pv_services:
            name = item["name"]
            code = item["code"]
            seen_names.append(name.lower())

            obj = Service.objects.filter(
                server=server, name__iexact=name
            ).first()

            if obj:
                if not dry_run:
                    obj.code = code
                    obj.status = "active"
                    obj.save()
                updated += 1
            else:
                if not dry_run:
                    Service.objects.create(
                        name=name,
                        code=code,
                        server=server,
                        status="active",
                    )
                created += 1

        deactivated = 0
        for s in Service.objects.filter(server=server):
            if s.name.lower() not in seen_names and s.status != "inactive":
                if not dry_run:
                    s.status = "inactive"
                    s.save()
                deactivated += 1

        self.stdout.write(
            f"Services: {created} created, {updated} updated, {deactivated} deactivated"
        )

        self.stdout.write(
            self.style.SUCCESS("PVAPins catalog sync complete!")
        )