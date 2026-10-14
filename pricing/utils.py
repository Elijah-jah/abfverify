import time
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.cache import cache
from django.utils import timezone

from pricing.models import Pricing, PricingConfiguration


def apply_pricing(usd_cost, config):
    """Your formula: cost_ngn = usd * rate, sell = cost + fixed_profit."""
    cost = (Decimal(str(usd_cost)) * config.exchange_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return cost, cost + config.fixed_profit


def throttle_provider_call(gap_seconds=1.5, key="instantnums_last_call"):
    """Minimum gap between provider calls — avoids the 502 rate-limit wall."""
    last = cache.get(key, 0)
    wait = gap_seconds - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    cache.set(key, time.time(), timeout=120)


def get_selling_price(provider, service, country, max_age_minutes=30):
    """
    Cached price if fresh; otherwise one polite live call to InstantNums,
    converted with YOUR PricingConfiguration and saved. Returns (row, price).
    """
    row = Pricing.objects.filter(service=service, country=country).first()
    if row and row.updated_at >= timezone.now() - timedelta(minutes=max_age_minutes):
        return row, row.selling_price

    config = PricingConfiguration.objects.first()
    if not config:
        return row, (row.selling_price if row else None)

    throttle_provider_call()
    try:
        p = provider.get_price(service.code, country.name)
    except Exception:
        return row, (row.selling_price if row else None)

    if not p.get("success") or "price_usd" not in p:
        return row, (row.selling_price if row else None)

    cost_ngn, sell_ngn = apply_pricing(p["price_usd"], config)
    row, _ = Pricing.objects.update_or_create(
        service=service,
        country=country,
        defaults={
            "provider_cost": cost_ngn,
            "selling_price": sell_ngn,
            "is_available": p.get("available", 0) > 0,
            "status": "active",
        },
    )
    return row, sell_ngn