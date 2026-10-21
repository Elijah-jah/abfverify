import logging

from django.contrib import admin, messages

from providers.factory import get_provider

from .models import Order

logger = logging.getLogger(__name__)


def expire_stuck_orders(modeladmin, request, queryset):
    """Cancel provider-side (if still alive) and expire - no charge to user."""
    done = 0
    for order in queryset.filter(status='waiting'):
        try:
            get_provider(server=order.provider).cancel(order.provider_order_id)
        except Exception as e:
            logger.warning('Provider cancel failed for %s: %s', order.order_id, e)
        order.status = 'expired'
        order.save(update_fields=['status', 'updated_at'])
        done += 1
    messages.success(request, f'{done} stuck order(s) expired. Customers were not charged.')


expire_stuck_orders.short_description = 'Expire stuck waiting orders (no charge)'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "order_id",
        "user",
        "country",
        "service",
        "phone_number",
        "price",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "country",
        "service",
        "provider",
        "created_at",
    )

    search_fields = (
        "order_id",
        "user__username",
        "user__email",
        "phone_number",
        "provider_order_id",
    )

    readonly_fields = (
        "order_id",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 25

    actions = [
        "expire_stuck_orders",
    ]

    fieldsets = (

        ("Order Information", {
            "fields": (
                "order_id",
                "user",
                "status",
            )
        }),

        ("Service Details", {
            "fields": (
                "country",
                "service",
                "phone_number",
                "provider",
                "provider_order_id",
            )
        }),

        ("Payment", {
            "fields": (
                "price",
            )
        }),

        ("SMS", {
            "fields": (
                "sms_code",
            )
        }),

        ("Dates", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )