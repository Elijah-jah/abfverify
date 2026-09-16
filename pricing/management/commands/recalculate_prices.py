from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import F

from pricing.models import Pricing, PricingConfiguration


class Command(BaseCommand):
    help = (
        "Recompute all selling prices from stored provider costs + "
        "current profit config. No provider API calls."
    )

    def handle(self, *args, **options):
        config = PricingConfiguration.objects.first()

        if config is None:
            raise Exception("Pricing Configuration has not been created.")

        profit = config.fixed_profit

        Pricing.objects.update(
            selling_price=F("provider_cost") + profit
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"All prices recalculated with profit ₦{profit}"
            )
        )