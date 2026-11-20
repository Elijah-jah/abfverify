import logging

from django.db import transaction

from wallet.models import Transaction, Wallet

from .models import GiftGroup, GiftOrder, GiftOrderImage

logger = logging.getLogger(__name__)

MAX_GIFT_IMAGES = 5
MAX_GIFT_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB per photo after client compression
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class GiftOrderError(Exception):
    """Order placement failed. ``field`` optionally points at a form field."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field


def validate_gift_images(images):
    """Validate customer photos before any wallet charge happens."""
    images = [image for image in (images or []) if image]
    if len(images) > MAX_GIFT_IMAGES:
        raise GiftOrderError(
            f"You can attach at most {MAX_GIFT_IMAGES} photos to one gift order.",
            field="images",
        )
    for image in images:
        content_type = getattr(image, "content_type", "") or ""
        if content_type and content_type.lower() not in ALLOWED_IMAGE_TYPES:
            raise GiftOrderError(
                f"{image.name} is not a supported image. Please upload JPG, PNG, WEBP or GIF photos.",
                field="images",
            )
        if image.size > MAX_GIFT_IMAGE_SIZE:
            raise GiftOrderError(
                f"{image.name} is larger than 10 MB. Please choose a smaller photo.",
                field="images",
            )
    return images


REQUIRED_FIELDS = (
    ("sender_name", "Sender's name", 150),
    ("receiver_name", "Receiver's name", 150),
    ("address", "Address", None),
    ("city", "City", 100),
    ("state", "State", 100),
    ("zip_code", "Zip code", 20),
    ("phone", "Phone number", 30),
)


@transaction.atomic
def create_gift_order(user, group_id, form_data, images=None):
    """Validate, charge the wallet and create the order.

    Everything runs in one transaction: if the wallet charge fails,
    no order row is left behind. The Transaction record means the
    purchase shows up on the Transactions page and dashboard activity
    automatically.
    """
    images = validate_gift_images(images)

    group = (
        GiftGroup.objects.select_for_update()
        .select_related("category")
        .filter(pk=group_id, is_active=True, category__is_active=True)
        .first()
    )
    if group is None:
        raise GiftOrderError("This gift is no longer available.")

    cleaned = {}
    for field, label, max_length in REQUIRED_FIELDS:
        value = (form_data.get(field) or "").strip()
        if not value:
            raise GiftOrderError(f"Please enter the {label.lower()}.", field=field)
        if max_length and len(value) > max_length:
            raise GiftOrderError(f"{label} is too long ({max_length} characters max).", field=field)
        cleaned[field] = value

    # Optional gift note from the sender
    cleaned["note"] = (form_data.get("note") or "").strip()

    wallet = Wallet.objects.select_for_update().get(user=user)
    if wallet.balance < group.price:
        raise GiftOrderError(
            f"Insufficient balance. This gift costs \u20A6{group.price:,.2f}, "
            f"but your wallet balance is \u20A6{wallet.balance:,.2f}."
        )

    image_url = ""
    if group.image:
        try:
            image_url = group.image.url
        except (ValueError, AttributeError):
            image_url = ""

    order = GiftOrder.objects.create(
        user=user,
        group=group,
        group_name=group.name,
        category_name=group.category.name,
        group_image_url=image_url,
        price=group.price,
        status="pending",
        **cleaned,
    )

    for image in images:
        GiftOrderImage.objects.create(order=order, image=image)

    wallet.balance -= group.price
    wallet.save(update_fields=["balance"])

    Transaction.objects.create(
        user=user,
        amount=group.price,
        transaction_type="payment",
        status="successful",
        description=f"Gift order {order.order_id} \u2014 {group.name}",
    )

    return order
