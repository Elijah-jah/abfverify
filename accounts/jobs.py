import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events, register_job
from django.utils import timezone
from django.db import transaction
from datetime import timedelta

from orders.models import Order
from providers.factory import get_provider
from wallet.models import Wallet, Transaction
from boost.models import BoostOrder, OPEN_STATUSES
from boost.providers import ReallySimpleSocial

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")


@register_job(scheduler, "interval", minutes=1, id="expire_orders", replace_existing=True)
def expire_orders_job():
    print(">>> SCHEDULER RAN AT", timezone.now(), "<<<")

    now = timezone.now()
    expired_count = 0

    # 1. EXPIRE WAITING ORDERS (no SMS after 20 min) - NO REFUND NEEDED
    waiting_orders = Order.objects.filter(status="waiting")
    for order in waiting_orders:
        expires_at = order.created_at + timedelta(minutes=20)  # Changed from 7 to 20

        if now >= expires_at:
            # Get correct provider based on server stored in order
            provider = get_provider(server=order.provider)

            # Cancel with provider (free up number)
            try:
                provider.cancel(order.provider_order_id)
            except Exception as e:
                logger.warning("Provider cancel failed for expired order %s on server %s: %s",
                               order.order_id, order.provider, str(e))

            order.status = "expired"
            order.save(update_fields=["status", "updated_at"])
            expired_count += 1
            logger.info("Expired order %s on server %s (no charge)", order.order_id, order.provider)

    print(f">>> Total processed this run: {expired_count} <<<")
    return expired_count


@register_job(scheduler, "interval", seconds=30, id="deliver_waiting_orders", replace_existing=True)
def deliver_waiting_orders_job():
    """Server-side SMS delivery sweep: polls providers for orders still
    waiting on a code, delivers + charges atomically.

    This is the GUARANTEED delivery path - it does not depend on the
    customer keeping a browser tab open. The webhook remains the fast
    path (~1s). Both check 'waiting'/'pending' status under a row lock,
    so they can never double-charge.

    Load discipline: zero provider calls when nothing is waiting; at most
    6 orders per run with 5s between calls -> worst case ~360 calls/hour
    only while orders are pending. Works for both servers (server1 =
    InstantNums, server2 = DaisySMS) via order.provider."""
    orders = list(
        Order.objects
        .filter(status__in=("waiting", "pending"))  # CHANGED: cover pending too
        .select_related("service")
        .order_by("created_at")[:6]
    )
    if not orders:
        return 0

    print(">>> DELIVERY SWEEP RAN AT", timezone.now(), "-",
          len(orders), "waiting orders <<<")

    delivered = 0
    for order in orders:
        try:
            provider = get_provider(server=order.provider)
            result = provider.check_sms(order.provider_order_id)
        except Exception as e:
            logger.warning("Delivery poll failed for %s on %s: %s",
                           order.order_id, order.provider, str(e))
            time.sleep(5)
            continue

        time.sleep(5)  # stay well under the provider rate cap

        if result.get("status") != "finished":
            continue

        # Deliver + charge atomically - identical rules to the webhook path
        try:
            with transaction.atomic():
                locked = Order.objects.select_for_update().get(pk=order.pk)
                if locked.status not in ("waiting", "pending"):  # CHANGED
                    continue  # webhook beat us to it
                wallet = Wallet.objects.select_for_update().get(user=locked.user)
                if wallet.balance < locked.price:
                    logger.warning("Delivery sweep: insufficient funds for %s",
                                   locked.order_id)
                    continue
                wallet.balance -= locked.price
                wallet.save(update_fields=["balance"])
                Transaction.objects.create(
                    user=locked.user,
                    amount=locked.price,
                    transaction_type="payment",
                    status="successful",
                    description=f"Payment for {locked.service.name} number ({locked.phone_number})",
                )
                locked.sms_code = result.get("sms")
                locked.full_sms = result.get("full_sms", "")
                locked.sms_received_at = timezone.now()
                locked.status = "received"
                locked.save(update_fields=["sms_code", "full_sms",
                                           "sms_received_at", "status", "updated_at"])
                delivered += 1
                logger.info("Delivery sweep delivered %s (%s)",
                            locked.order_id, locked.phone_number)
        except Exception:
            logger.exception("Delivery sweep error for %s", order.order_id)

    print(f">>> Delivery sweep: {delivered} delivered this run <<<")
    return delivered


@register_job(scheduler, "interval", minutes=5, id="sync_boost_orders", replace_existing=True)
def sync_boost_orders_job():
    """Update open boost orders from ReallySimpleSocial (batch of up to 100)."""
    open_orders = list(
        BoostOrder.objects.filter(status__in=OPEN_STATUSES)
        .values_list("provider_order_id", flat=True)[:100]
    )
    if not open_orders:
        return

    print(">>> BOOST SYNC RAN AT", timezone.now(), "-", len(open_orders), "open orders <<<")

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
