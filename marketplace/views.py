from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction, models
from django.http import JsonResponse
from .models import (
    LogProduct, LogCategory, LogItem, LogPurchase,
    LogOrderCounter
)
from wallet.models import Wallet, Transaction
from orders.models import Order


@login_required
def services_view(request):
    """Buy Logs marketplace page."""
    query = request.GET.get("q", "").strip().lower()
    products = LogProduct.objects.select_related("category", "sub_category").all()
    categories = LogCategory.objects.prefetch_related("subcategories").all()

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
            "query": request.GET.get("q", ""),
            "user_wallet": wallet,
        },
    )


@login_required
@require_POST
def purchase_log(request, product_id):
    """Atomic purchase endpoint."""
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
                        "error": f"Insufficient funds. You need ₦{product.price:,.2f} but your balance is ₦{wallet.balance:,.2f}.",
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
                    "username": purchase.username,
                    "password": purchase.password,
                    "price": str(purchase.price),
                }
            )

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": "Something went wrong. Please try again."},
            status=500,
        )