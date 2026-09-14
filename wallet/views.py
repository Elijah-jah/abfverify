import uuid
import requests
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from django.db import models
from .models import Wallet, Transaction
from orders.models import Order


def update_pending_transactions(user):

    expired_time = timezone.now() - timedelta(minutes=1)

    pending_transactions = Transaction.objects.filter(
        user=user,
        status="pending",
        created_at__lte=expired_time
    )

    for transaction in pending_transactions:
        transaction.status = "failed"
        transaction.save()


@login_required
def fund_wallet(request):

    # Mark expired pending transactions as failed
    update_pending_transactions(request.user)

    if request.method == "POST":

        amount = request.POST.get("amount")

        if not amount:
            return JsonResponse({
                "error": "Amount is required"
            })

        # PocketFi takes NAIRA directly - no kobo conversion needed
        reference = uuid.uuid4().hex[:20]

        url = f"{settings.POCKETFI_BASE_URL}/api/v1/checkout/request"

        headers = {
            "Authorization": f"Bearer {settings.POCKETFI_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        data = {
            "first_name": request.user.first_name or "Customer",
            "last_name": request.user.last_name or "Customer",
            "phone": request.POST.get("phone", "0000000000"),  # required by PocketFi
            "business_id": settings.POCKETFI_BUSINESS_ID,
            "email": request.user.email,
            # carry our own reference through the redirect
            "redirect_link": f"{settings.POCKETFI_CALLBACK_URL}?reference={reference}",
            "amount": str(amount),
        }

        response = requests.post(
            url,
            json=data,
            headers=headers,
        )

        result = response.json()

        if result.get("status") == "success" and result.get("payment_link"):

            Transaction.objects.create(
                user=request.user,
                amount=Decimal(amount),
                transaction_type="deposit",
                reference=reference,
                payment_id=result["payment_id"],
                status="pending",
                description="Wallet funding via PocketFi",
            )

            return JsonResponse({
                "payment_url": result["payment_link"]
            })

        return JsonResponse({
            "error": result.get("message") or "Could not initialize payment"
        })

    return JsonResponse({
        "error": "Invalid request"
    })


@login_required
def verify_payment(request):

    reference = request.GET.get("reference")

    if not reference:
        return redirect("wallet")

    transaction = Transaction.objects.filter(
        reference=reference,
        user=request.user
    ).first()

    if not transaction:
        return redirect("wallet")

    # prevents double-crediting if user refreshes the callback page
    if transaction.status == "successful":
        return redirect("wallet")

    url = f"{settings.POCKETFI_BASE_URL}/api/v1/checkout/confirm"

    headers = {
        "Authorization": f"Bearer {settings.POCKETFI_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        url,
        json={"payment_id": transaction.payment_id},
        headers=headers,
    )

    result = response.json()

    if result.get("status") == "success":

        # PocketFi returns amount in naira (e.g. "100.00") - no /100 needed
        amount = Decimal(result["amount"])

        wallet, created = Wallet.objects.get_or_create(
            user=request.user
        )

        wallet.balance += amount
        wallet.save()

        transaction.status = "successful"

    else:

        transaction.status = "failed"

    transaction.save()

    return redirect("wallet")


@login_required
def transactions_page(request):

    update_pending_transactions(request.user)

    transactions = Transaction.objects.filter(
        user=request.user
    ).order_by("-created_at")  # Changed to descending (newest first)

    user_wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    # Calculate total spent from payment transactions (new way) and orders (old way)
    total_spent_transactions = Transaction.objects.filter(
        user=request.user,
        transaction_type="payment",
        status="successful",
    ).aggregate(total=models.Sum("amount"))["total"] or 0

    total_spent_orders = Order.objects.filter(
        user=request.user,
        status__in=["completed", "received"],
    ).aggregate(total=models.Sum("price"))["total"] or 0

    # Use the higher value to catch all deductions
    total_spent = max(total_spent_transactions, total_spent_orders)

    return render(
        request,
        "panel/transactions.html",
        {
            "transactions": transactions,
            "user_wallet": user_wallet,
            "total_spent": total_spent,
        }
    )


@login_required
def wallet_page(request):

    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    return render(
        request,
        "panel/wallet.html",
        {
            "wallet": wallet
        }
    )