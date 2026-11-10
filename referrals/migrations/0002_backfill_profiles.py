# Gives every EXISTING user a referral code (new users get one via signal).

from django.db import migrations


def backfill_profiles(apps, schema_editor):
    from referrals.models import generate_referral_code

    User = apps.get_model("accounts", "User")
    ReferralProfile = apps.get_model("referrals", "ReferralProfile")

    existing = set(ReferralProfile.objects.values_list("user_id", flat=True))
    batch = []

    for user in User.objects.exclude(id__in=existing).iterator():
        batch.append(
            ReferralProfile(user_id=user.id, code=generate_referral_code())
        )
        if len(batch) >= 500:
            ReferralProfile.objects.bulk_create(batch)
            batch = []

    if batch:
        ReferralProfile.objects.bulk_create(batch)


class Migration(migrations.Migration):

    dependencies = [
        ("referrals", "0001_initial"),
        ("accounts", "0006_user_first_name_user_last_name_user_phone"),
    ]

    operations = [
        migrations.RunPython(backfill_profiles, migrations.RunPython.noop),
    ]
