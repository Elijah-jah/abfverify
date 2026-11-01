from django.core.management.base import BaseCommand, CommandError

from countries.models import Country
from pricing.services import PricingService
from providers.instantnums import InstantNumsProvider
from services.models import Service


class Command(BaseCommand):
    help = 'Import or update InstantNums Signal USA pricing only.'

    def handle(self, *args, **options):
        provider = InstantNumsProvider()

        # Signal's InstantNums service ID, confirmed from the provider catalog.
        service, _ = Service.objects.update_or_create(
            provider_id=829,
            defaults={
                'server': 'server1',
                'code': 'Signal',
                'name': 'Signal',
                'status': 'active',
            },
        )

        # Find USA in InstantNums's country catalog.
        countries_data = provider.get_countries()
        countries = countries_data.get('countries', [])

        country_data = next(
            (
                item for item in countries
                if (
                    str(item.get('name', '')).strip().lower()
                    in {'united states', 'usa', 'united states of america'}
                    or str(item.get('short_name', '')).strip().upper()
                    == 'US'
                )
            ),
            None,
        )

        if country_data is None:
            raise CommandError(
                'United States was not found in the InstantNums catalog.'
            )

        country, _ = Country.objects.update_or_create(
            server='server1',
            provider_id=country_data['ID'],
            defaults={
                'name': country_data['name'],
                'iso_code': country_data.get('short_name', ''),
                'phone_code': country_data.get('cc', ''),
                'status': 'active',
            },
        )

        self.stdout.write(
            f'Fetching Signal USA price from InstantNums: '
            f'service={service.code}, country={country.name}...'
        )

        price_data = provider.get_price(
            service.code,
            country.name,
        )

        if not price_data.get('success'):
            raise CommandError(
                f'InstantNums price request failed: {price_data}'
            )

        if 'price_usd' not in price_data:
            raise CommandError(
                f'InstantNums returned no price_usd value: {price_data}'
            )

        # Uses the existing PricingConfiguration exchange rate and profit.
        pricing = PricingService.update_price_from_rate(
            country=country,
            service=service,
            price_usd=price_data['price_usd'],
            server='server1',
        )

        pricing.is_available = True
        pricing.save(update_fields=['is_available', 'updated_at'])

        self.stdout.write(
            self.style.SUCCESS(
                f'Imported: {service.name} | {country.name} | '
                f'Provider cost: ₦{pricing.provider_cost} | '
                f'Selling price: ₦{pricing.selling_price}'
            )
        )
