# Adds "referral" and "redeem" transaction types.
# (Choices-only change - no database schema change required.)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wallet", "0010_wallet_virtual_account_name_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="transaction_type",
            field=models.CharField(
                choices=[
                    ("deposit", "Deposit"),
                    ("withdrawal", "Withdrawal"),
                    ("payment", "Payment"),
                    ("refund", "Refund"),
                    ("referral", "Referral Bonus"),
                    ("redeem", "Code Redemption"),
                ],
                default="deposit",
                max_length=20,
            ),
        ),
    ]
