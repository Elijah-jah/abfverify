# from django.core.management.base import BaseCommand
# from django.utils import timezone
# from datetime import timedelta
# from django.db import transaction
# from wallet.models import Wallet, Transaction
# from orders.models import Order
# from providers.factory import get_provider
# import logging

# logger = logging.getLogger(__name__)


# class Command(BaseCommand):
#     help = "Expire waiting orders older than 7 minutes and refund wallets"

#     def handle(self, *args, **options):
#         self.stdout.write(self.style.SUCCESS(f"Running expiry check at {timezone.now()}"))

#     def handle(self, *args, **options):
#         waiting_orders = Order.objects.filter(status="waiting")
#         provider = get_provider()
#         now = timezone.now()
#         expired_count = 0

#         for order in waiting_orders:
#             expires_at = order.created_at + timezone.timedelta(minutes=7)

#             if now >= expires_at:
#                 if not order.sms_code and not order.refund_processed:
#                     try:
#                         provider.cancel_order(order.provider_order_id)
#                     except Exception as e:
#                         logger.warning("Provider cancel failed for expired order %s: %s", order.order_id, str(e))

#                     with transaction.atomic():
#                         wallet = Wallet.objects.select_for_update().get(user=order.user)
#                         wallet.balance += order.price
#                         wallet.save(update_fields=["balance"])

#                         Transaction.objects.create(
#                             user=order.user,
#                             amount=order.price,
#                             transaction_type="refund",
#                             status="successful",
#                             reference=f"EXP-{order.order_id}",
#                             description=f"Refund for expired order {order.order_id}",
#                         )

#                         order.refund_processed = True

#                 order.status = "expired"
#                 order.save(update_fields=["status", "refund_processed", "updated_at"])
#                 expired_count += 1
#                 self.stdout.write(self.style.SUCCESS(f"Expired order {order.order_id}"))

#         self.stdout.write(self.style.SUCCESS(f"Total expired: {expired_count}"))