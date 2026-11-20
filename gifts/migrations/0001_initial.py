import uuid
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GiftCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("display_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name_plural": "Gift categories",
                "ordering": ["display_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="GiftGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True, default="")),
                ("image", models.ImageField(blank=True, max_length=255, null=True, upload_to="gifts/groups/")),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                    ),
                ),
                (
                    "delivery_duration",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text='Shown to customers, e.g. "3-5 business days". Leave blank to hide it.',
                        max_length=100,
                    ),
                ),
                ("display_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="groups",
                        to="gifts.giftcategory",
                    ),
                ),
            ],
            options={
                "verbose_name": "Gift group",
                "verbose_name_plural": "Gift groups",
                "ordering": ["display_order", "name"],
                "unique_together": {("category", "name")},
            },
        ),
        migrations.CreateModel(
            name="GiftOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_id", models.CharField(editable=False, max_length=24, unique=True)),
                ("group_name", models.CharField(max_length=160)),
                ("category_name", models.CharField(max_length=100)),
                ("group_image_url", models.URLField(blank=True, default="", max_length=500)),
                ("price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("sender_name", models.CharField(max_length=150)),
                ("receiver_name", models.CharField(max_length=150)),
                ("address", models.TextField()),
                ("city", models.CharField(max_length=100)),
                ("state", models.CharField(max_length=100)),
                ("zip_code", models.CharField(max_length=20)),
                ("phone", models.CharField(max_length=30)),
                ("tracking_link", models.URLField(blank=True, default="", max_length=500)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("completed", "Completed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="orders",
                        to="gifts.giftgroup",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gift_orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="GiftOrderImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(max_length=255, upload_to="gifts/orders/%Y/%m/")),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to="gifts.giftorder",
                    ),
                ),
            ],
            options={
                "ordering": ["id"],
            },
        ),
    ]
