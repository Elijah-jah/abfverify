from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from countries.models import Country
from services.models import Service
from pricing.models import Pricing
from providers.factory import get_provider


class Command(BaseCommand):
    help = "Import one service + its pricing for one country on a server."

    def add_arguments(self, parser):
        parser.add_argument("--country", required=True, help='e.g. "Indonesia"')
        parser.add_argument("--service-code", required=True, help="Provider code, e.g. fb")
        parser.add_argument("--service-name", default="Facebook")
        parser.add_argument("--selling-price", type=float, required=True, help="Your price in NGN")
        parser.add_argument("--server", default="server1")

    def handle(self, *args, **opts):
        server = opts["server"]

        country = Country.objects.filter(
            name__icontains=opts["country"], server=server
        ).first()
        if not country:
            raise CommandError(f'No country matching "{opts["country"]}" found on {server}')

        provider = get_provider(server=server)

        # ---- 1. Find provider cost (try the country's possible codes) ----
        cost = None
        candidates = [country.iso_code, str(country.iso_code).lower(), str(country.phone_code)]
        for code in dict.fromkeys(c for c in candidates if c):
            try:
                data = provider.get_price(opts["service-code"], code)
                self.stdout.write(f"RAW price response ({code}): {data}")
                for key in ("price", "price_usd", "cost", "rate"):
                    if data.get(key) is not None:
                        cost = Decimal(str(data[key]))
                        break
                if cost is not None:
                    break
            except Exception as e:
                self.stdout.write(f"Price fetch failed with country code '{code}': {e}")

        if cost is None:
            raise CommandError(
                "Could not determine provider cost. Check the RAW response above "
                "and tell me the exact field name."
            )

        # ---- 2. Get or create the service ----
        service = Service.objects.filter(
            provider_id=opts["service-code"], server=server
        ).first()
        if not service:
            CategoryModel = Service._meta.get_field("category").remote_field.model
            category = CategoryModel.objects.first()
            if not category:
                category = CategoryModel.objects.create(name="Social")
            max_order = Service.objects.filter(server=server).count()
            service = Service.objects.create(
                name=opts["service-name"],
                provider_id=opts["service-code"],
                code=opts["service-code"],
                category=category,
                server=server,
                status="active",
                display_order=max_order + 1,
            )
            self.stdout.write(self.style.SUCCESS(f"Created service: {service}"))
        else:
            self.stdout.write(f"Service already exists: {service}")

        # ---- 3. Get or create the pricing row ----
        pricing, created = Pricing.objects.get_or_create(
            country=country,
            service=service,
            defaults={
                "provider_cost": cost,
                "selling_price": Decimal(str(opts["selling_price"])),
                "status": "active",
            },
        )
        if not created:
            pricing.provider_cost = cost
            pricing.selling_price = Decimal(str(opts["selling_price"]))
            pricing.status = "active"
            pricing.save()
            self.stdout.write("Pricing row existed - updated with new prices")
        else:
            self.stdout.write(self.style.SUCCESS("Pricing row created"))

        self.stdout.write("------------------------------------------------")
        self.stdout.write(f"Country       : {country.name} ({server})")
        self.stdout.write(f"Service       : {service.name} [{service.provider_id}]")
        self.stdout.write(f"Provider cost : ${cost}")
        self.stdout.write(f"Selling price : NGN {opts['selling_price']}")
        self.stdout.write(self.style.SUCCESS("Done - check the services page."))
