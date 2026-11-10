import logging

from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from wallet.models import Transaction, Wallet

from .models import RedeemCode, ReferralProfile

logger = logging.getLogger(__name__)


@ratelimit(key="user", rate="10/m", method="POST", block=True)
@login_required
@require_POST
def redeem_code_view(request):
    """Redeem a one-time ABFverify code. The code's amount is credited
    to the user's wallet exactly once (row lock + is_redeemed flag).
    Limited to ONE successful redeem per user per day."""
    code_input = (request.POST.get("code") or "").strip().upper()

    if not code_input:
        return JsonResponse(
            {"success": False, "error": "Please enter a code."},
            status=400,
        )

    # One redeem per user per day
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    redeemed_today = Transaction.objects.filter(
        user=request.user,
        transaction_type="redeem",
        status="successful",
        created_at__gte=today_start,
    ).exists()

    if redeemed_today:
        return JsonResponse(
            {"success": False, "error": "You can only redeem 1 code per day. Come back tomorrow!"},
            status=429,
        )

    with transaction.atomic():
        redeem = (
            RedeemCode.objects
            .select_for_update()
            .filter(code__iexact=code_input)
            .first()
        )

        if not redeem:
            return JsonResponse(
                {"success": False, "error": "Invalid code. Please check it and try again."},
                status=404,
            )

        if redeem.is_redeemed:
            return JsonResponse(
                {"success": False, "error": "This code has already been used."},
                status=400,
            )

        redeem.is_redeemed = True
        redeem.redeemed_by = request.user
        redeem.redeemed_at = timezone.now()
        redeem.save(update_fields=["is_redeemed", "redeemed_by", "redeemed_at"])

        Wallet.objects.filter(user=request.user).update(
            balance=models.F("balance") + redeem.amount
        )
        Transaction.objects.create(
            user=request.user,
            amount=redeem.amount,
            transaction_type="redeem",
            status="successful",
            reference=f"REDEEM-{redeem.id}",
            description=f"Redeemed code {redeem.code}",
        )

        new_balance = (
            Wallet.objects.filter(user=request.user)
            .values_list("balance", flat=True)
            .first()
        )

    logger.info(
        "Code redeemed: %s by %s (N%s)",
        redeem.code, request.user.email, redeem.amount,
    )

    return JsonResponse({
        "success": True,
        "code": redeem.code,
        "amount": f"{redeem.amount:.2f}",
        "new_balance": f"{new_balance:.2f}" if new_balance is not None else None,
    })


@login_required
@require_POST
def dismiss_referral_card(request):
    """Records when the user dismissed the dashboard referral card.
    The card re-appears 6 hours later (checked in the dashboard view)."""
    profile, _ = ReferralProfile.objects.get_or_create(user=request.user)
    profile.card_dismissed_at = timezone.now()
    profile.save(update_fields=["card_dismissed_at"])
    return JsonResponse({"success": True})