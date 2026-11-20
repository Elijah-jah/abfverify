def pending_gift_orders(request):
    """Pending gift order count for the staff notification bell on finance pages."""
    if request.user.is_authenticated and request.user.is_staff:
        from .models import GiftOrder
        return {
            "pending_gift_orders_count": GiftOrder.objects.filter(status="pending").count(),
        }
    return {"pending_gift_orders_count": 0}
