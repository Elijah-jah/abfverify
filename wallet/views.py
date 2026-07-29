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

        amount_kobo = int(float(amount) * 100)

        url = "https://api.paystack.co/transaction/initialize"

        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "email": request.user.email,
            "amount": amount_kobo,
            "callback_url": settings.PAYSTACK_CALLBACK_URL
        }

        response = requests.post(
            url,
            json=data,
            headers=headers
        )

        result = response.json()

        if result.get("status"):

            reference = result["data"]["reference"]

            Transaction.objects.create(
                user=request.user,
                amount=Decimal(amount),
                transaction_type="deposit",
                reference=reference,
                status="pending",
                description="Wallet funding via Paystack"
            )

            return JsonResponse({
                "payment_url": result["data"]["authorization_url"]
            })

        return JsonResponse({
            "error": result.get("message")
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

    url = f"https://api.paystack.co/transaction/verify/{reference}"

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
    }

    response = requests.get(
        url,
        headers=headers
    )

    result = response.json()

    if result.get("status") and result["data"]["status"] == "success":

        amount = Decimal(
            result["data"]["amount"]
        ) / Decimal(100)

        wallet, created = Wallet.objects.get_or_create(
            user=request.user
        )

        old_balance = wallet.balance

        wallet.balance += amount
        wallet.save()

        if wallet.balance > old_balance:
            transaction.status = "successful"
        else:
            transaction.status = "failed"

        transaction.save()

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