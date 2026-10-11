import logging
from .models import BoostOrder, OPEN_STATUSES
from .providers import ReallySimpleSocial

logger = logging.getLogger(__name__)


def sync_boost_orders_job():
    """Update open boost orders from the provider. Runs on a schedule."""
    open_orders = list(
        BoostOrder.objects.filter(status__in=OPEN_STATUSES)
        .values_list("provider_order_id", flat=True)[:100]
    )
    if not open_orders:
        return

    try:
        provider = ReallySimpleSocial()
        results = provider.get_orders_status(open_orders)
    except Exception:
        logger.exception("Boost status sync failed")
        return

    if not isinstance(results, dict):
        return

    for order_id, info in results.items():
        if not isinstance(info, dict) or "error" in info:
            continue
        BoostOrder.objects.filter(provider_order_id=str(order_id)).update(
            status=info.get("status", "Pending"),
            remains=str(info.get("remains", "")),
            start_count=str(info.get("start_count", "")),
        )