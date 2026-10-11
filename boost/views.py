import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from wallet.models import Wallet, Transaction
from .models import BoostService, BoostOrder, BoostSettings, OPEN_STATUSES
from .providers import ReallySimpleSocial, ReallySimpleSocialError

logger = logging.getLogger(__name__)


@login_required
def boost_view(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    boost_settings = BoostSettings.get_solo()

    ajax = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.POST.get("ajax") == "1"
    )

    def ajax_error_response(redirect_to="boost"):
        if ajax:
            msg_text, msg_level = "", "error"
            for m in messages.get_messages(request):
                msg_text = str(m)
                msg_level = m.level_tag
            return JsonResponse({
                "success": False,
                "message": msg_text,
                "level": msg_level,
                "redirect": reverse(redirect_to),
            })
        return redirect(redirect_to)

    if request.method == "POST":
        service = get_object_or_404(BoostService, pk=request.POST.get("service"), is_active=True)
        link = (request.POST.get("link") or "").strip()
        try:
            quantity = int(request.POST.get("quantity") or 0)
        except ValueError:
            quantity = 0

        if not link:
            messages.error(request, "Please paste the link to boost.")
            return ajax_error_response("boost")

        if quantity < service.min_order or quantity > service.max_order:
            messages.error(
                request,
                f"Quantity must be between {service.min_order:,} and {service.max_order:,} for this service."
            )
            return ajax_error_response("boost")

        price = service.sell_price(quantity, boost_settings)

        # Wallet check including pending boost orders
        pending_total = BoostOrder.objects.filter(
            user=request.user, status__in=OPEN_STATUSES,
        ).aggregate(total=Sum("price"))["total"] or 0

        if wallet.balance < pending_total + price:
            messages.error(request, "Your balance is low. Please recharge to continue.")
            return ajax_error_response("wallet")

        provider = ReallySimpleSocial()
        try:
            provider_order_id = provider.add_order(
                service_id=service.service_id,
                link=link,
                quantity=quantity,
            )
        except ReallySimpleSocialError as e:
            logger.exception("Boost order failed for user %s: %s", request.user.id, e)
            messages.error(request, "Unable to place boost order. Please try again later.")
            return ajax_error_response("boost")

        # Provider accepted — charge the wallet and record the order
        wallet.balance = wallet.balance - price
        wallet.save(update_fields=["balance"])

        Transaction.objects.create(
            user=request.user,
            transaction_type="payment",
            status="successful",
            amount=price,
            description=f"Boost: {service.name} x{quantity}",
        )

        order = BoostOrder.objects.create(
            user=request.user,
            service=service,
            link=link,
            quantity=quantity,
            price=price,
            provider_cost=(service.rate / 1000) * quantity,
            provider_order_id=str(provider_order_id),
        )

        if ajax:
            return JsonResponse({
                "success": True,
                "message": "Boost order placed! It usually starts within minutes.",
                "order": {
                    "id": order.id,
                    "provider_order_id": order.provider_order_id,
                    "service_name": order.service.name,
                    "link": order.link,
                    "quantity": order.quantity,
                    "price": str(order.price),
                    "status": order.status,
                },
            })

        messages.success(request, "Boost order placed!")
        return redirect("boost")

    services = list(
        BoostService.objects.filter(is_active=True)
        .values("id", "service_id", "name", "category", "rate", "min_order", "max_order")
    )
    recent_orders = BoostOrder.objects.filter(user=request.user)[:20]

    return render(request, "panel/boost.html", {
        "wallet": wallet,
        "user_wallet": wallet,
        "boost_settings": boost_settings,
        "services_json": services,
        "orders": recent_orders,
    })


@login_required
def boost_order_status(request):
    order = get_object_or_404(
        BoostOrder, pk=request.GET.get("order_id"), user=request.user
    )
    return JsonResponse({
        "success": True,
        "status": order.status,
        "remains": order.remains,
        "start_count": order.start_count,
    })