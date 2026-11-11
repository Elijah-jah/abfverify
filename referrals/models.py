import random
import string
from decimal import Decimal

from django.conf import settings
from django.db import models

# Tiered referral rewards: (number of depositing referrals, naira reward).
# Each tier pays out ONCE, in order, as the referrer reaches it.
REFERRAL_TIERS = (
    (2, Decimal("500")),
    (5, Decimal("800")),
    (10, Decimal("1000")),
    (20, Decimal("2000")),
    (30, Decimal("4000")),
)

# Instant bonus for a NEW user who signs up with a referral code.
SIGNUP_BONUS = Decimal("200")

# How often the dashboard referral card re-appears after dismissal.
REFERRAL_CARD_INTERVAL_HOURS = 6
# Minimum FIRST deposit for a referral to count toward tier rewards.
MIN_FIRST_DEPOSIT = Decimal("500")

def generate_referral_code():
    """Unique user-facing referral code, e.g. ABF7K2QX9P."""
    while True:
        code = "ABF" + "".join(random.choices(string.ascii_uppercase + string.digits, k=7))
        if not ReferralProfile.objects.filter(code=code).exists():
            return code


def generate_redeem_code():
    """Unique 10-char one-time redeem code, e.g. 9XK2M7QZ4A."""
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        if not RedeemCode.objects.filter(code=code).exists():
            return code


class ReferralProfile(models.Model):
    """One per user. Holds their referral code, who referred them,
    whether they've made their first deposit, and the 6-hour
    dashboard card dismissal timestamp."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_profile",
    )
    code = models.CharField(
        max_length=12,
        unique=True,
        default=generate_referral_code,
    )
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals_made",
    )
    # True once this user has made their FIRST successful deposit.
    qualified = models.BooleanField(default=False)
        # True once the user's FIRST deposit has been checked. The first
    # deposit is the only one that can ever qualify them - if it's
    # below the minimum, later deposits never count.
    first_deposit_seen = models.BooleanField(default=False)
    # Server-side 6-hour tracking for the dashboard referral card.
    card_dismissed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.code})"


class ReferralReward(models.Model):
    """One row per tier payout. unique_together guarantees a tier
    can never be paid twice to the same referrer."""

    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_rewards",
    )
    tier = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("referrer", "tier")
        ordering = ["tier"]

    def __str__(self):
        return f"{self.referrer.username} - {self.tier} referrals - N{self.amount}"


class RedeemCode(models.Model):
    """One-time admin-generated code. Redeeming credits the wallet."""

    code = models.CharField(
        max_length=32,
        unique=True,
        default=generate_redeem_code,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_redeemed = models.BooleanField(default=False)
    redeemed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="redeemed_codes",
    )
    redeemed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        status = "USED" if self.is_redeemed else "ACTIVE"
        return f"{self.code} - N{self.amount} ({status})"
