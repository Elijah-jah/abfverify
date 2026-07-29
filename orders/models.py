from django.db import models
from django.conf import settings
import uuid


class Order(models.Model):

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("waiting", "Waiting for SMS"),
        ("received", "SMS Received"),  # NEW
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )

    order_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
    )

    country = models.ForeignKey(
        "countries.Country",
        on_delete=models.PROTECT,
        related_name="orders",
    )

    service = models.ForeignKey(
        "services.Service",
        on_delete=models.PROTECT,
        related_name="orders",
    )

    phone_number = models.CharField(
        max_length=25,
        blank=True,
        null=True,
    )

    provider = models.CharField(
        max_length=50,
        default="InstantNums",
    )

    provider_order_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    sms_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    full_sms = models.TextField(  # NEW
        blank=True,
        null=True,
    )

    # Prevents an order from being refunded more than once
    # refund_processed = models.BooleanField(
    #     default=False,
    # )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    sms_received_at = models.DateTimeField(  # NEW
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"ABF-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_id} - {self.phone_number or 'No Number'}"