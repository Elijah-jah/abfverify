from django.db import models, transaction
from django.conf import settings
import os


def log_image_path(instance, filename):
    ext = filename.split('.')[-1]
    return f'log_images/{instance.id or "new"}_{instance.title[:20]}.{ext}'


class LogCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(
        max_length=50,
        default="fa-solid fa-box",
        help_text="FontAwesome class, e.g., fa-solid fa-shield-halved"
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "Log Categories"

    def __str__(self):
        return self.name


class LogSubCategory(models.Model):
    category = models.ForeignKey(
        LogCategory, on_delete=models.CASCADE, related_name="subcategories"
    )
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Log Sub Categories"

    def __str__(self):
        return f"{self.category.name} — {self.name}"


class LogProduct(models.Model):
    category = models.ForeignKey(
        LogCategory, on_delete=models.CASCADE, related_name="products", null=True, blank=True
    )
    sub_category = models.ForeignKey(
        LogSubCategory, on_delete=models.CASCADE, related_name="products", null=True, blank=True
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to=log_image_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def in_stock(self):
        return self.items.filter(status="available").count()


class LogItem(models.Model):
    STATUS_CHOICES = (
        ("available", "Available"),
        ("sold", "Sold"),
    )

    product = models.ForeignKey(
        LogProduct, on_delete=models.CASCADE, related_name="items"
    )
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="available"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.title} — {self.username}"


class LogOrderCounter(models.Model):
    """Atomic counter for ABFLOGS order IDs."""
    last_number = models.PositiveIntegerField(default=12344)

    @classmethod
    def get_next(cls):
        with transaction.atomic():
            counter, _ = cls.objects.select_for_update().get_or_create(pk=1)
            counter.last_number += 1
            counter.save()
            return counter.last_number


class LogPurchase(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="log_purchases",
    )
    order_id = models.CharField(
        max_length=20, unique=True, editable=False
    )
    log_item = models.OneToOneField(
        LogItem, on_delete=models.CASCADE, related_name="purchase"
    )
    product_title = models.CharField(max_length=200)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"ABFLOGS{LogOrderCounter.get_next()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_id} — {self.product_title}"