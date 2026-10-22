from django.db import models
from django.utils import timezone


class SMSRecharge(models.Model):
    SERVER_CHOICES = (
        ("server1", "InstantNums (Server 1)"),
        ("server2", "DaisySMS (Server 2)"),
    )

    server = models.CharField(max_length=20, choices=SERVER_CHOICES, default="server1")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "SMS Recharge"
        verbose_name_plural = "SMS Recharges"

    def __str__(self):
        return f"{self.get_server_display()} - N{self.amount:,.2f}"


class BoostFunding(models.Model):
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Boost Funding"
        verbose_name_plural = "Boost Fundings"

    def __str__(self):
        return f"Boost funding - N{self.amount:,.2f}"


class LogBatch(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
    )

    product = models.ForeignKey(
        "marketplace.LogProduct",
        on_delete=models.CASCADE,
        related_name="batches",
    )
    quantity = models.PositiveIntegerField()
    cost = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text="How much you paid for this batch. Leave empty = stays PENDING.",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", editable=False)
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.cost is not None:
            self.status = "confirmed"
            if self.confirmed_at is None:
                self.confirmed_at = timezone.now()
        else:
            self.status = "pending"
            self.confirmed_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        cost = f"N{self.cost:,.2f}" if self.cost is not None else "PENDING"
        return f"{self.product.title} x{self.quantity} - {cost}"
