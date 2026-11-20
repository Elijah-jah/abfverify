from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gifts", "0003_giftorder_tracking_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="giftgroup",
            name="has_shoe_sizes",
            field=models.BooleanField(default=False, verbose_name="Shoe size"),
        ),
        migrations.AddField(
            model_name="giftgroup",
            name="has_cloth_sizes",
            field=models.BooleanField(default=False, verbose_name="Cloth size"),
        ),
        migrations.AddField(
            model_name="giftgroup",
            name="has_frame_sizes",
            field=models.BooleanField(default=False, verbose_name="Frame size"),
        ),
        migrations.AddField(
            model_name="giftgroup",
            name="has_ring_sizes",
            field=models.BooleanField(default=False, verbose_name="Ring size"),
        ),
        migrations.AddField(
            model_name="giftorder",
            name="size_info",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
    ]
