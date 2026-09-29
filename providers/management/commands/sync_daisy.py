from django.core.management.base import BaseCommand, CommandError

from countries.models import Country
from services.models import Service
from providers.factory import get_provider

USA_COUNTRY_ID = 187


class Command(BaseCommand):
    help = "Create USA country + all DaisySMS service rows (server2)"

    def handle(self, *args, **options):
        server = "server2"

        # --- Sanity check: provider must answer with this key BEFORE we touch the DB ---
        try:
            provider = get_provider(server=server)
            balance = provider.get_balance() if hasattr(provider, "get_balance") else None
        except PermissionError as e:
            raise CommandError(f"DaisySMS rejected the API key: {e}")
        except Exception as e:
            raise CommandError(f"Could not reach DaisySMS: {e}")

        if balance is not None:
            self.stdout.write(f"DaisySMS connected. Balance: {balance}")

        # --- ONE API call for all USA services ---
        try:
            rates = provider.get_all_prices(USA_COUNTRY_ID)
        except PermissionError as e:
            raise CommandError(f"DaisySMS rejected the API key: {e}")
        except Exception as e:
            raise CommandError(f"get_all_prices failed: {e}")

        if not rates:
            raise CommandError("DaisySMS returned 0 services — aborting without changes.")

        # --- Ensure USA country exists ---
        country, country_created = Country.objects.get_or_create(
            name="USA",
            server=server,
            defaults={"iso_code": "US", "status": "active"},
        )
        self.stdout.write(f"USA country: {'created' if country_created else 'already exists'}")

        # --- Create one Service row per provider code ---
        created, existing = 0, 0
        for code in rates:
            _, was_created = Service.objects.get_or_create(
                server=server,
                code=code.strip().lower(),
                defaults={
                    "name": code.replace("_", " ").title(),
                    "status": "active",
                },
            )
            if was_created:
                created += 1
            else:
                existing += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done: {created} new services, {existing} already existed, "
            f"{len(rates)} offered by provider (USA)"
        ))