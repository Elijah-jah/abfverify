from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events, register_job
from django.utils import timezone
from datetime import timedelta
from orders.models import Order
from providers.factory import get_provider
from boost.models import BoostOrder, OPEN_STATUSES
from boost.providers import ReallySimpleSocial
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")


@register_job(scheduler, "interval", minutes=1, id="expire_orders", replace_existing=True)
def expire_orders_job():
    print(">>> SCHEDULER RAN AT", timezone.now(), "<<<")

    now = timezone.now()
    expired_count = 0

    # 1. EXPIRE WAITING ORDERS (no SMS after 20 min) — NO REFUND NEEDED
    waiting_orders = Order.objects.filter(status="waiting")
    for order in waiting_orders:
        expires_at = order.created_at + timedelta(minutes=20)  # Changed from 7 to 20

        if now >= expires_at:
            # Get correct provider based on server stored in order
            provider = get_provider(server=order.provider)

            # Cancel with provider (free up number)
            try:
                provider.cancel_order(order.provider_order_id)
            except Exception as e:
                logger.warning("Provider cancel failed for expired order %s on server %s: %s",
                               order.order_id, order.provider, str(e))

            order.status = "expired"
            order.save(update_fields=["status", "updated_at"])
            expired_count += 1
            logger.info("Expired order %s on server %s (no charge)", order.order_id, order.provider)

    print(f">>> Total processed this run: {expired_count} <<<")
    return expired_count


@register_job(scheduler, "interval", minutes=5, id="sync_boost_orders", replace_existing=True)
def sync_boost_orders_job():
    """Update open boost orders from ReallySimpleSocial (batch of up to 100)."""
    open_orders = list(
        BoostOrder.objects.filter(status__in=OPEN_STATUSES)
        .values_list("provider_order_id", flat=True)[:100]
    )
    if not open_orders:
        return

    print(">>> BOOST SYNC RAN AT", timezone.now(), "—", len(open_orders), "open orders <<<")

    try:
        provider = ReallySimpleSocial()
        results = provider.get_orders_status(open_orders)
    except Exception as e:
        logger.exception("Boost status sync failed: %s", e)
        return

    if not isinstance(results, dict):
        return

    updated = 0
    for order_id, info in results.items():
        if not isinstance(info, dict) or "error" in info:
            continue
        BoostOrder.objects.filter(provider_order_id=str(order_id)).update(
            status=info.get("status", "Pending"),
            remains=str(info.get("remains", "")),
            start_count=str(info.get("start_count", "")),
        )
        updated += 1

    print(f">>> Boost orders updated this run: {updated} <<<")
    return updated


register_events(scheduler)