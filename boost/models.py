from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models


class BoostSettings(models.Model):
    """Singleton — edit exchange rate & profit from admin, like SMS pricing."""
    exchange_rate = models.DecimalField(
        max_digits=10, decimal_places=2, default=1.0,
        help_text="Provider currency → NGN. Your provider bills in NGN, so keep this at 1.0.",
    )
    profit_flat = models.DecimalField(
        max_digits=10, decimal_places=2, default=1000.0,
        help_text="Minimum profit (NGN) on EVERY order. 1000 = you never earn less than ₦1,000.",
    )
    profit_percent = models.DecimalField(
        max_digits=6, decimal_places=2, default=15.0,
        help_text="Extra profit on top, as % of provider cost. This is what makes BIG orders pay more. 15 = 15%.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Boost Settings"
        verbose_name_plural = "Boost Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Rate {self.exchange_rate} · +₦{self.profit_flat} + {self.profit_percent}%"


class BoostService(models.Model):
    """Synced from ReallySimpleSocial API."""
    service_id = models.PositiveIntegerField(unique=True)  # provider's ID
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255, blank=True, db_index=True)
    service_type = models.CharField(max_length=100, blank=True)
    description = models.TextField(
        blank=True, default="",
        help_text="Shown to users on the order form (e.g. what link to paste)",
    )
    rate = models.DecimalField(max_digits=12, decimal_places=4, help_text="Provider cost per 1000 units")
    min_order = models.PositiveIntegerField(default=1)
    max_order = models.PositiveIntegerField(default=1000)
    refill = models.BooleanField(default=False)
    cancel = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"[{self.service_id}] {self.name}"

    def sell_price(self, quantity, settings_obj=None):
        """What the customer pays in NGN for `quantity` units."""
        settings_obj = settings_obj or BoostSettings.get_solo()
        qty = Decimal(quantity)
        provider_cost = (self.rate / Decimal("1000")) * qty
        profit = settings_obj.profit_flat + (provider_cost * settings_obj.profit_percent / Decimal("100"))
        price = (provider_cost + profit) * settings_obj.exchange_rate
        return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


OPEN_STATUSES = ["Pending", "Processing", "In progress"]


class BoostOrder(models.Model):
    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Processing", "Processing"),
        ("In progress", "In progress"),
        ("Completed", "Completed"),
        ("Partial", "Partial"),
        ("Canceled", "Canceled"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="boost_orders")
    service = models.ForeignKey(BoostService, on_delete=models.PROTECT, related_name="orders")
    link = models.URLField(max_length=500)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)          # what user paid (NGN)
    provider_cost = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    provider_order_id = models.CharField(max_length=50, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending", db_index=True)
    start_count = models.CharField(max_length=50, blank=True, default="")
    remains = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Boost #{self.provider_order_id} — {self.service.name} x{self.quantity}"