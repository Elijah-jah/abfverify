import logging

from django.db import models, transaction

from wallet.models import Transaction, Wallet

from .models import (
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


def process_first_deposit(user):
    """Call after a successful wallet deposit. If this is the user's
    FIRST deposit, mark them qualified and pay the referrer any tier
    rewards that are now due (each tier pays once, in order).

    Returns the number of tier rewards paid.
    """
    profile = get_or_create_profile(user)

    if profile.qualified:
        return 0  # not their first deposit - nothing to do

    profile.qualified = True
    profile.save(update_fields=["qualified"])

    referrer = profile.referred_by
    if not referrer:
        return 0

    qualified_count = ReferralProfile.objects.filter(
        referred_by=referrer, qualified=True
    ).count()

    paid = 0
    for tier, amount in REFERRAL_TIERS:
        if qualified_count < tier:
            continue
        with transaction.atomic():
            # unique_together (referrer, tier) makes this race-safe:
            # even if two deposits process at the same moment, the
            # reward row can only be created once.
            reward, created = ReferralReward.objects.get_or_create(
                referrer=referrer,
                tier=tier,
                defaults={"amount": amount},
            )
            if not created:
                continue
            Wallet.objects.filter(user=referrer).update(
                balance=models.F("balance") + amount
            )
            Transaction.objects.create(
                user=referrer,
                amount=amount,
                transaction_type="referral",
                status="successful",
                reference=f"REF-TIER-{tier}-{referrer.id}",
                description=(
                    f"Referral reward: {tier} referrals made their first deposit"
                ),
            )
            paid += 1
            logger.info(
                "Referral tier paid: %s reached %s depositing referrals (N%s)",
                referrer.email, tier, amount,
            )

    return paid
