from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gifts", "0002_giftorder_note"),
    ]

    operations = [
        migrations.AlterField(
            model_name="giftorder",
            name="tracking_link",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]
