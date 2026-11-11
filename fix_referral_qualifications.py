"""
One-time fix: re-check every referred user who hasn't qualified yet.

Run it ONCE on Render Shell with:

    python fix_referral_qualifications.py

It finds every user who signed up with a referral code but is not
qualified yet, and re-runs the qualification check. Anyone who has
already made a deposit of N500 or more qualifies immediately, the
referrer's progress bar moves, and any completed stage reward is
paid out. Safe to run more than once - already-qualified users are
skipped automatically.
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from referrals.models import ReferralProfile
from referrals.services import process_first_deposit


def main():
    pending = ReferralProfile.objects.filter(
        qualified=False, referred_by__isnull=False
    ).select_related("user")

    total = pending.count()
    print(f"Checking {total} referred user(s)...")

    fixed = 0
    for p in pending:
        process_first_deposit(p.user)
        p.refresh_from_db()
        if p.qualified:
            fixed += 1
            print(f"  QUALIFIED: {p.user.email}")

    print(f"Done. {fixed} of {total} user(s) qualified.")


if __name__ == "__main__":
    main()