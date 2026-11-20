"""Site-wide branding + admin-home stats exposed to every template."""

from .models import SiteSettings


def site_settings(request):
    return {"site_settings": SiteSettings.load()}


def admin_home_stats(request):
    """Stats for the custom admin landing page (staff hitting /semilore/ only)."""
    if not request.path.startswith("/semilore/") or not request.user.is_staff:
        return {}

    try:
        from django.contrib.auth import get_user_model

        from gifts.models import GiftOrder
        from wallet.models import Transaction

        try:
            from boost.models import BoostOrder

            boost_orders_total = BoostOrder.objects.count()
            boost_orders_pending = BoostOrder.objects.filter(status="Pending").count()
        except Exception:
            boost_orders_total = boost_orders_pending = 0

        return {
            "admin_home_stats": {
                "users_total": get_user_model().objects.count(),
                "gift_orders_total": GiftOrder.objects.count(),
                "gift_orders_pending": GiftOrder.objects.filter(status="pending").count(),
                "boost_orders_total": boost_orders_total,
                "boost_orders_pending": boost_orders_pending,
                "transactions_total": Transaction.objects.count(),
            }
        }
    except Exception:
        # Never break the admin home because a stat query failed.
        return {}
