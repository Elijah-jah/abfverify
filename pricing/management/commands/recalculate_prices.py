import time
from django.core.management.base import BaseCommand
from django.db.models import F
from django.db import OperationalError

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

        for attempt in range(5):
            try:
                Pricing.objects.update(
                    selling_price=F("provider_cost") + profit
                )
                break
            except OperationalError:
                self.stdout.write("Deadlock — retrying in 5s...")
                time.sleep(5)
        else:
            raise Exception("Deadlocked 5 times. Try again in a few minutes.")

        self.stdout.write(
            self.style.SUCCESS(
                f"All prices recalculated with profit ₦{profit}"
            )
        )