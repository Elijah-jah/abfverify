from decimal import Decimal, ROUND_HALF_UP

from pricing.models import Pricing, PricingConfiguration


class PricingService:

    @staticmethod
    def update_price_from_rate(country, service, price_usd, server="server2"):
        """
        Update a Pricing row when the USD price is already known
        (used by the bulk `update_prices` command).

        The provider price is converted to NGN using the configured
        exchange rate, then the fixed profit is added to get the
        selling price.
        """
        config = PricingConfiguration.objects.first()

        if config is None:
            raise Exception(
                "Pricing Configuration has not been created."
            )

        provider_price_usd = Decimal(str(price_usd))

        provider_price_ngn = (
            provider_price_usd * config.exchange_rate
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        selling_price = (
            provider_price_ngn + config.fixed_profit
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        pricing, created = Pricing.objects.update_or_create(
            country=country,
            service=service,
            defaults={
                "provider_cost": provider_price_ngn,
                "selling_price": selling_price,
                "status": "active",
            },
        )

        return pricing