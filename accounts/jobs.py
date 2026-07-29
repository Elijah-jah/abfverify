from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events, register_job
from django.utils import timezone
from datetime import timedelta
from orders.models import Order
from providers.factory import get_provider
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


register_events(scheduler)


@register_job(scheduler, "interval", days=3, id="update_prices", replace_existing=True)
def update_prices_job():
    from django.core.management import call_command
    print(">>> UPDATING PRICES AT", timezone.now(), "<<<")
    try:
        call_command("update_prices")
        print(">>> PRICE UPDATE COMPLETE <<<")
    except Exception as e:
        print(f">>> PRICE UPDATE FAILED: {e} <<<")