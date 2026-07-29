from django.core.management.base import BaseCommand
from countries.models import Country
from services.models import Service
from pricing.services import PricingService
from providers.factory import get_provider


class Command(BaseCommand):
    help = 'Update all prices from providers'

    def handle(self, *args, **kwargs):
        servers = ['server2', 'server3']
        
        for server in servers:
            try:
                provider = get_provider(server=server)
            except ValueError:
                continue

            countries = Country.objects.filter(status='active', server=server)
            services = Service.objects.filter(status='active', server=server)

            for country in countries:
                for service in services:
                    try:
                        PricingService.update_price(
                            country=country,
                            service=service,
                            server=server,
                        )
                        self.stdout.write(self.style.SUCCESS(
                            'Updated: ' + server + ' | ' + country.name + ' | ' + service.name
                        ))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            'Failed: ' + server + ' | ' + country.name + ' | ' + service.name + ' | ' + str(e)
                        ))

        self.stdout.write(self.style.SUCCESS('Price update complete!'))
