from django.db import models
from countries.models import Country
from services.models import Service
from decimal import Decimal


class Pricing(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("inactive", "Inactive"),
    )

    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="pricing"
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="pricing"
    )

    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    provider_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    estimated_delivery_time = models.PositiveIntegerField(
        default=30,
        help_text="Estimated OTP delivery time in seconds"
    )

    is_available = models.BooleanField(default=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="active"
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("country", "service")
        ordering = ["country", "service"]

    def __str__(self):
        return f"{self.country.name} - {self.service.name}"
    



class PricingConfiguration(models.Model):
    exchange_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("1600.00"),
        help_text="NGN equivalent of 1 USD",
    )

    fixed_profit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("250.00"),
        help_text="Fixed profit added to each number",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pricing Configuration"
        verbose_name_plural = "Pricing Configuration"

    def __str__(self):
        return "Global Pricing Configuration"