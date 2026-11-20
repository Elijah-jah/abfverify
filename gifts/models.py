import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

# The size lists a customer can pick from, per size type. The admin only
# ticks which types apply to a gift group; these are the choices shown.
SIZE_OPTIONS = {
    "shoe": [str(n) for n in range(10, 46)],
    "cloth": ["XS", "S", "M", "L", "XL", "XXL", "XXXL"],
    "frame": [
        "4x6 in", "5x7 in", "6x8 in", "8x10 in", "8x12 in",
        "10x12 in", "12x16 in", "16x20 in", "20x24 in",
    ],
    "ring": [str(n) + half for n in range(4, 15) for half in ("", ".5")] + ["15"],
}


class GiftCategory(models.Model):
    """Top level: e.g. Flowers, Frames, Hampers (the pill bar on the page)."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "Gift categories"

    def __str__(self):
        return self.name


class GiftGroup(models.Model):
    """The purchasable gift card: picture, name, price and delivery duration."""

    category = models.ForeignKey(
        GiftCategory,
        on_delete=models.PROTECT,
        related_name="groups",
    )
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, default="")
    image = models.ImageField(upload_to="gifts/groups/", blank=True, null=True, max_length=255)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    delivery_duration = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text='Shown to customers, e.g. "3-5 business days". Leave blank to hide it.',
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # Size checkboxes: tick whichever applies to this gift and the order
    # form will ask the customer for that size. All unticked = the form
    # shows nothing about sizes. Ticking is optional.
    has_shoe_sizes = models.BooleanField(default=False, verbose_name="Shoe size")
    has_cloth_sizes = models.BooleanField(default=False, verbose_name="Cloth size")
    has_frame_sizes = models.BooleanField(default=False, verbose_name="Frame size")
    has_ring_sizes = models.BooleanField(default=False, verbose_name="Ring size")

    created_at = models.DateTimeField(auto_now_add=True)

    # (key, model field, label shown to the customer)
    SIZE_FIELD_MAP = (
        ("shoe", "has_shoe_sizes", "Shoe"),
        ("cloth", "has_cloth_sizes", "Cloth"),
        ("frame", "has_frame_sizes", "Frame"),
        ("ring", "has_ring_sizes", "Ring"),
    )

    @property
    def size_types(self):
        """Enabled size type keys for this group, e.g. ["shoe", "cloth"]."""
        return [key for key, field, _label in self.SIZE_FIELD_MAP if getattr(self, field)]

    class Meta:
        ordering = ["display_order", "name"]
        unique_together = ("category", "name")
        verbose_name = "Gift group"
        verbose_name_plural = "Gift groups"

    def __str__(self):
        return f"{self.category.name} \u2014 {self.name}"


class GiftOrder(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gift_orders",
    )
    group = models.ForeignKey(
        GiftGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    order_id = models.CharField(max_length=24, unique=True, editable=False)

    # Snapshots so the order survives later edits to the group.
    group_name = models.CharField(max_length=160)
    category_name = models.CharField(max_length=100)
    group_image_url = models.URLField(max_length=500, blank=True, default="")
    price = models.DecimalField(max_digits=12, decimal_places=2)

    # Form details collected at checkout
    sender_name = models.CharField(max_length=150)
    receiver_name = models.CharField(max_length=150)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=30)
    note = models.TextField(blank=True, default="")  # optional message from the sender

    # Sizes the customer picked, e.g. "Shoe: 42 · Cloth: XL". Empty when
    # the gift group has no size checkboxes ticked.
    size_info = models.CharField(max_length=200, blank=True, default="")

    # Filled by staff on the finance page — accepts a tracking number,
    # a full tracking link, or any plain text.
    tracking_link = models.CharField(max_length=500, blank=True, default="")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"PGFT{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def can_mark_processing(self):
        return self.status == "pending"

    def can_mark_completed(self):
        return self.status in {"pending", "processing"}

    def __str__(self):
        return f"{self.order_id} \u2014 {self.group_name} \u2014 {self.status}"


class GiftOrderImage(models.Model):
    """A photo the customer attached to a gift order (up to 5)."""

    order = models.ForeignKey(
        GiftOrder,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="gifts/orders/%Y/%m/", max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Photo {self.pk} for order {self.order_id}"
