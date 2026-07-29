from django.core.management.base import BaseCommand

from countries.models import Country
from services.models import Service
from providers.factory import get_provider


class Command(BaseCommand):
    help = "Sync countries and services from InstantNums"

    def handle(self, *args, **kwargs):
        provider = get_provider()

        # ==========================
        # Sync Countries
        # ==========================

        self.stdout.write(
            self.style.SUCCESS("Fetching countries...")
        )

        countries_response = provider.get_countries()

        country_count = 0

        for item in countries_response.get("countries", []):

            iso_code = item["short_name"]
            name = item["name"]

            # Find existing country by ISO code
            country = Country.objects.filter(
                iso_code=iso_code
            ).first()

            if country:
                country.provider_id = item["ID"]
                country.name = name
                country.phone_code = item["cc"]
                country.status = "active"
                country.save()

            else:
                # Find existing country by name
                existing_name = Country.objects.filter(
                    name=name
                ).first()

                if existing_name:
                    existing_name.provider_id = item["ID"]
                    existing_name.iso_code = iso_code
                    existing_name.phone_code = item["cc"]
                    existing_name.status = "active"
                    existing_name.save()

                else:
                    Country.objects.create(
                        provider_id=item["ID"],
                        name=name,
                        iso_code=iso_code,
                        phone_code=item["cc"],
                        status="active",
                    )

            country_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Synced {country_count} countries"
            )
        )


        # ==========================
        # Sync Services
        # ==========================

        self.stdout.write(
            self.style.SUCCESS("Fetching services...")
        )

        services_response = provider.get_services()

        service_count = 0

        for item in services_response.get("services", []):

            provider_id = item["ID"]
            name = item["name"]

            # Find existing service by provider ID
            service = Service.objects.filter(
                provider_id=provider_id
            ).first()

            if service:
                service.name = name
                service.status = "active"
                service.save()

            else:
                # Find existing service by name
                existing_name = Service.objects.filter(
                    name=name
                ).first()

                if existing_name:
                    existing_name.provider_id = provider_id
                    existing_name.status = "active"
                    existing_name.save()

                else:
                    Service.objects.create(
                        provider_id=provider_id,
                        name=name,
                        status="active",
                    )

            service_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Synced {service_count} services"
            )
        )


        self.stdout.write(
            self.style.SUCCESS(
                "InstantNums sync completed successfully."
            )
        )