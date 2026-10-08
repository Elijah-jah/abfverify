import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import (
    LogProduct, LogCategory, LogItem, LogPurchase,
    LogOrderCounter,
)
from wallet.models import Wallet, Transaction

logger = logging.getLogger(__name__)


@login_required
def services_view(request):
    query = request.GET.get("q", "").strip().lower()

    # Show ALL products, annotate stock count
    products = LogProduct.objects.annotate(
        stock=Count("items", filter=Q(items__status="available"))
    ).select_related("category", "sub_category")

    categories = LogCategory.objects.prefetch_related("subcategories").all()
    log_purchases = LogPurchase.objects.filter(user=request.user).select_related("log_item")

    if query:
        products = products.filter(
            models.Q(title__icontains=query)
            | models.Q(description__icontains=query)
            | models.Q(sub_category__name__icontains=query)
            | models.Q(category__name__icontains=query)
        )

    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    return render(
        request,
        "panel/services.html",
        {
            "products": products,
            "categories": categories,
            "log_purchases": log_purchases,
            "query": request.GET.get("q", ""),
            "user_wallet": wallet,
        },
    )


@login_required
@require_POST
def purchase_log(request, product_id):
    """Atomic purchase endpoint with confirmation."""
    try:
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=request.user)

            available_items = list(
                LogItem.objects.filter(
                    product_id=product_id, status="available"
                ).values_list("id", flat=True)[:1]
            )

            if not available_items:
                return JsonResponse(
                    {"success": False, "error": "Sorry, this item is out of stock."},
                    status=400,
                )

            log_item = LogItem.objects.select_for_update().get(id=available_items[0])

            if log_item.status != "available":
                return JsonResponse(
                    {"success": False, "error": "Sorry, this item just sold out."},
                    status=400,
                )

            product = log_item.product

            if wallet.balance < product.price:
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"Insufficient funds. You need \u20A6{product.price:,.2f} but your balance is \u20A6{wallet.balance:,.2f}.",
                    },
                    status=400,
                )

            wallet.balance -= product.price
            wallet.save()

            log_item.status = "sold"
            log_item.save()

            purchase = LogPurchase.objects.create(
                user=request.user,
                log_item=log_item,
                product_title=product.title,
                username=log_item.username,
                password=log_item.password,
                email_password=log_item.email_password,
                two_fa=log_item.two_fa,
                recovery_email=log_item.recovery_email,
                price=product.price,
            )

            Transaction.objects.create(
                user=request.user,
                amount=product.price,
                transaction_type="payment",
                status="successful",
                description=f"Purchase of {product.title} ({purchase.order_id})",
            )

            return JsonResponse(
                {
                    "success": True,
                    "order_id": purchase.order_id,
                    "product_title": purchase.product_title,
                    "creds": purchase.creds,
                    "format_label": product.format_labels,
                    "price": str(purchase.price),
                    "new_balance": str(wallet.balance),
                }
            )

    except Exception:
        logger.exception("Log purchase failed for user %s, product %s", request.user.id, product_id)
        return JsonResponse(
            {"success": False, "error": "Something went wrong. Please try again."},
            status=500,
        )