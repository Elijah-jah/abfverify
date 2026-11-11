import logging

from django.db import models, transaction

from wallet.models import Transaction, Wallet

from .models import (
    MIN_FIRST_DEPOSIT,
    REFERRAL_TIERS,
    SIGNUP_BONUS,
    ReferralProfile,
    ReferralReward,
)

logger = logging.getLogger(__name__)


def get_or_create_profile(user):
    profile, _ = ReferralProfile.objects.get_or_create(user=user)
    return profile


def attach_referrer(new_user, code):
    """Link a freshly-registered user to the owner of `code` and pay
    the new user their instant signup bonus.

    Returns the referrer on success, None if the code was invalid,
    the user was already referred, or it was a self-referral.
    """
    code = (code or "").strip().upper()
    if not code:
        return None

    try:
        referrer_profile = (
            ReferralProfile.objects.select_related("user").get(code__iexact=code)
        )
    except ReferralProfile.DoesNotExist:
        return None

    referrer = referrer_profile.user
    if referrer.pk == new_user.pk:
        return None

    profile = get_or_create_profile(new_user)
    if profile.referred_by_id:
        return None  # already linked to someone

    profile.referred_by = referrer
    profile.save(update_fields=["referred_by"])

    with transaction.atomic():
        Wallet.objects.filter(user=new_user).update(
            balance=models.F("balance") + SIGNUP_BONUS
        )
        Transaction.objects.create(
            user=new_user,
            amount=SIGNUP_BONUS,
            transaction_type="referral",
            status="successful",
            reference=f"REF-SIGNUP-{new_user.id}",
            description=f"Referral signup bonus (code {code})",
        )

    logger.info(
        "Referral attached: %s referred by %s (bonus N%s)",
        new_user.email, referrer.email, SIGNUP_BONUS,
    )
    return referrer


def _cumulative_thresholds():
    """Stage sizes (2, 5, 10, 20, 30) as running totals, because each
    stage counts NEW qualifying referrals only:
    stage 1 = 2 total, stage 2 = 7, stage 3 = 17, stage 4 = 37, stage 5 = 67."""
    total = 0
    stages = []
    for size, amount in REFERRAL_TIERS:
        total += size
        stages.append((size, total, amount))
    return stages


def process_first_deposit(user, amount=None):
    """Call after EVERY successful wallet deposit.

    A referral qualifies the moment they make their FIRST deposit of
    MIN_FIRST_DEPOSIT or more. Smaller deposits are simply ignored -
    they never disqualify the user. Once qualified, later deposits
    change nothing.

    When a referral qualifies, the referrer is paid any stage rewards
    now due. Each stage resets: it needs NEW qualifying referrals
    (2, then 5 more, then 10 more, then 20 more, then 30 more).
    """
    with transaction.atomic():
        profile = ReferralProfile.objects.select_for_update().get_or_create(
            user=user
        )[0]

        # Already qualified - nothing more to do.
        if profile.qualified:
            return 0

        # Fallback: if the caller didn't pass the amount, check whether
        # the user has ANY successful deposit of the minimum or more.
        if amount is None:
            amount = (
                Transaction.objects
                .filter(
                    user=user,
                    transaction_type="deposit",
                    status="successful",
                    amount__gte=MIN_FIRST_DEPOSIT,
                )
                .order_by("created_at")
                .values_list("amount", flat=True)
                .first()
            )
            if amount is None:
                return 0  # no qualifying deposit yet

        # Deposit below the minimum - ignore it. The user can still
        # qualify whenever they make a deposit of MIN_FIRST_DEPOSIT+.
        if amount < MIN_FIRST_DEPOSIT:
            return 0

        profile.qualified = True
        profile.first_deposit_seen = True
        profile.save(update_fields=["qualified", "first_deposit_seen"])

        referrer = profile.referred_by
        if not referrer:
            return 0

        qualified_count = ReferralProfile.objects.filter(
            referred_by=referrer, qualified=True
        ).count()

        paid = 0
        for size, threshold, reward_amount in _cumulative_thresholds():
            if qualified_count < threshold:
                continue
            # unique_together (referrer, tier) makes this race-safe:
            # each stage can only ever be paid once per referrer.
            reward, created = ReferralReward.objects.get_or_create(
                referrer=referrer,
                tier=size,
                defaults={"amount": reward_amount},
            )
            if not created:
                continue
            Wallet.objects.filter(user=referrer).update(
                balance=models.F("balance") + reward_amount
            )
            Transaction.objects.create(
                user=referrer,
                amount=reward_amount,
                transaction_type="referral",
                status="successful",
                reference=f"REF-TIER-{size}-{referrer.id}",
                description=(
                    f"Referral reward: {size} new referrals deposited "
                    f"\u20A6{MIN_FIRST_DEPOSIT:.0f}+"
                ),
            )
            paid += 1
            logger.info(
                "Referral stage paid: %s completed %s-user stage (N%s)",
                referrer.email, size, reward_amount,
            )

    return paid