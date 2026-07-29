from decimal import Decimal, ROUND_HALF_UP

from pricing.models import Pricing, PricingConfiguration
from providers.factory import get_provider


class PricingService:

    @staticmethod
    def update_price(country, service, server="server3"):
        """
        Fetch the latest provider price,
        convert it to NGN,
        apply profit,
        and update the Pricing table.
        """

        provider = get_provider(server=server)

        config = PricingConfiguration.objects.first()

        if config is None:
            raise Exception(
                "Pricing Configuration has not been created."
            )

        print("\n========== PRICING DEBUG ==========")
        print("Server:", server)
        print("Country:", country.name)
        print("Service:", service.name)
        print("Service Code:", service.code)
        print("Service Provider ID:", service.provider_id)

        # Use correct identifier based on server
        if server == "server2":
            service_identifier = service.code  # DaisySMS uses full names like "amazon"
            country_identifier = 187  # USA is always 187 for DaisySMS
        else:
            service_identifier = service.provider_id
            country_identifier = country.provider_id

        response = provider.get_price(
            service=service_identifier,
            country=country_identifier,
        )

        print("Provider Response:", response)

        if not response.get("success"):
            raise Exception(
                f"Provider returned an error: {response}"
            )

        provider_price_usd = Decimal(
            str(response["price_usd"])
        )

        print("Provider Price (USD):", provider_price_usd)

        provider_price_ngn = (
            provider_price_usd * config.exchange_rate
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        print("Exchange Rate:", config.exchange_rate)
        print("Provider Cost (NGN):", provider_price_ngn)

        selling_price = (
            provider_price_ngn + config.fixed_profit
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        print("Fixed Profit:", config.fixed_profit)
        print("Selling Price:", selling_price)

        pricing, created = Pricing.objects.update_or_create(
            country=country,
            service=service,
            defaults={
                "provider_cost": provider_price_ngn,
                "selling_price": selling_price,
                "status": "active",
                "is_available": True,
            },
        )

        if created:
            print("Pricing record created.")
        else:
            print("Pricing record updated.")

        print("========== END DEBUG ==========\n")

        return pricing