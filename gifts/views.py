from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from wallet.models import Wallet

from .models import GiftCategory, GiftGroup, GiftOrder
from .services import GiftOrderError, create_gift_order


@login_required
def gift_sending(request):
    groups = GiftGroup.objects.filter(is_active=True).select_related("category")
    categories = (
        GiftCategory.objects.filter(is_active=True, groups__is_active=True)
        .distinct()
        .prefetch_related(Prefetch("groups", queryset=groups))
    )
    return render(request, "panel/gift_sending.html", {
        "categories": categories,
    })


@login_required
@require_POST
def gift_order_create(request, group_id):
    try:
        order = create_gift_order(
            user=request.user,
            group_id=group_id,
            form_data=request.POST,
            images=request.FILES.getlist("images"),
        )
    except GiftOrderError as exc:
        payload = {"success": False, "error": str(exc)}
        if getattr(exc, "field", None):
            payload["errors"] = {exc.field: [str(exc)]}
        return JsonResponse(payload, status=400)
    except Exception:
        # Never leak a 500 to the customer — log it and fail gracefully.
        import logging
        logging.getLogger(__name__).exception("Gift order failed for user %s", request.user.id)
        return JsonResponse({
            "success": False,
            "error": "We could not place your gift order right now. Please try again shortly.",
        }, status=500)

    wallet = Wallet.objects.filter(user=request.user).first()
    return JsonResponse({
        "success": True,
        "order_id": order.order_id,
        "group_name": order.group_name,
        "price": str(order.price),
        "new_balance": str(wallet.balance if wallet else 0),
        "message": "Your gift order has been placed.",
    })


@login_required
def my_gift_orders(request):
    orders = (
        GiftOrder.objects.filter(user=request.user)
        .prefetch_related("images")
    )
    return render(request, "panel/my_gift_orders.html", {
        "orders": orders,
    })
