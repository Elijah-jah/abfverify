
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from marketplace.models import LogProduct

from .models import BoostFunding, LogBatch, SMSRecharge
from .services import (
    get_analytics_context,
    get_dashboard_stats,
    get_rewards_context,
    get_sales_inventory,
)


def _clean_amount(raw):
    """Parse a positive Decimal from form input, or return None."""
    try:
        amount = Decimal(str(raw).strip())
    except (InvalidOperation, TypeError, ValueError, AttributeError):
        return None
    return amount if amount > 0 else None


def _get_untracked_restock():
    """Products with uploaded LogItems not yet covered by a LogBatch.

    Returns a list of dicts: {"product": ..., "quantity": ...}
    """
    untracked = []
    products = LogProduct.objects.annotate(uploaded=Count("items"))
    for p in products:
        recorded = (
            LogBatch.objects.filter(product=p)
            .aggregate(s=Sum("quantity"))["s"] or 0
        )
        diff = p.uploaded - recorded
        if diff > 0:
            untracked.append({"product": p, "quantity": diff})
    return untracked


@staff_member_required
@never_cache
def dashboard(request):
    stats = get_dashboard_stats()
    products = LogProduct.objects.all().order_by("title")
    untracked_list = _get_untracked_restock()
    return render(
        request,
        "finance/dashboard.html",
        {
            "stats": stats,
            "products": products,
            "untracked": untracked_list[0] if untracked_list else None,
        },
    )


@staff_member_required
@never_cache
def analytics(request):
    """All-time or date-ranged sales analytics with no stale browser cache."""
    context = get_analytics_context(request.GET.get("range", "all"))
    return render(request, "finance/analytics.html", context)


@staff_member_required
@never_cache
def inventory(request):
    """Product-level log, SMS, and boost sales for a selected period."""
    context = get_sales_inventory(request.GET.get("range", "today"))
    return render(request, "finance/inventory.html", context)


@staff_member_required
@require_POST
def record_untracked_restock(request):
    """Popup submission: record cost for unrecorded uploads."""
    product_id = request.POST.get("product_id")
    product = LogProduct.objects.filter(id=product_id).first()
    if product is None:
        return redirect("finance_dashboard")

    cost = _clean_amount(request.POST.get("cost"))
    if cost is None:
        messages.error(request, "Enter the total amount you spent on this upload.")
        return redirect("finance_dashboard")

    # Recompute quantity server-side   never trust the form
    untracked = [u for u in _get_untracked_restock() if u["product"].id == product.id]
    if not untracked:
        messages.info(request, "This upload is already recorded.")
        return redirect("finance_dashboard")

    quantity = untracked[0]["quantity"]
    LogBatch.objects.create(product=product, quantity=quantity, cost=cost)
    messages.success(request, f"Recorded restock - {product.title}: {quantity} units at ₦{cost:,.2f}")
    return redirect("finance_dashboard")


@staff_member_required
@require_POST
def add_sms_recharge(request):
    server = request.POST.get("server", "").strip()
    amount = _clean_amount(request.POST.get("amount"))
    note = request.POST.get("note", "").strip()

    if server not in ("server1", "server2"):
        messages.error(request, "Pick a provider: Server 1 (InstantNums) or Server 2 (DaisySMS).")
        return redirect("finance_dashboard")
    if amount is None:
        messages.error(request, "Enter a valid amount greater than zero.")
        return redirect("finance_dashboard")

    SMSRecharge.objects.create(server=server, amount=amount, note=note)
    label = "InstantNums" if server == "server1" else "DaisySMS"
    messages.success(request, f"Recharge recorded - {label}: ₦{amount:,.2f}")
    return redirect("finance_dashboard")


@staff_member_required
@require_POST
def add_boost_funding(request):
    amount = _clean_amount(request.POST.get("amount"))
    note = request.POST.get("note", "").strip()

    if amount is None:
        messages.error(request, "Enter a valid amount greater than zero.")
        return redirect("finance_dashboard")

    BoostFunding.objects.create(amount=amount, note=note)
    messages.success(request, f"Boost funding recorded - ₦{amount:,.2f}")
    return redirect("finance_dashboard")


@staff_member_required
@require_POST
def add_log_batch(request):
    product_id = request.POST.get("product")
    quantity_raw = request.POST.get("quantity", "").strip()
    cost_raw = request.POST.get("cost", "").strip()
    note = request.POST.get("note", "").strip()

    product = LogProduct.objects.filter(id=product_id).first()
    if product is None:
        messages.error(request, "Pick the log product you restocked.")
        return redirect("finance_dashboard")

    try:
        quantity = int(quantity_raw)
        if quantity <= 0:
            raise ValueError
    except (TypeError, ValueError):
        messages.error(request, "Enter a valid quantity.")
        return redirect("finance_dashboard")

    cost = None
    if cost_raw:
        cost = _clean_amount(cost_raw)
        if cost is None:
            messages.error(request, "Cost must be a valid amount   or leave it empty to keep the batch PENDING.")
            return redirect("finance_dashboard")

    batch = LogBatch.objects.create(
        product=product, quantity=quantity, cost=cost, note=note
    )
    if batch.status == "confirmed":
        messages.success(request, f"Restock confirmed - {product.title}: {quantity} units at ₦{cost:,.2f}")
    else:
        messages.warning(request, f"Restock added as PENDING - {product.title}: {quantity} units. Enter the cost later to confirm it.")
    return redirect("finance_dashboard")


@staff_member_required
@never_cache
def rewards(request):
    """Referral & redeem-code payout tracking (money given to users)."""
    return render(request, "finance/rewards.html", get_rewards_context())


# ---------------------------------------------------------------------------
# Gift orders (gifts app) — staff management pages
# ---------------------------------------------------------------------------

@staff_member_required
@never_cache
def gift_orders(request):
    """List every customer gift order, filterable by status."""
    from gifts.models import GiftOrder

    status_filter = request.GET.get("status", "")
    orders = (
        GiftOrder.objects
        .select_related("user")
        .prefetch_related("images")
    )
    if status_filter in {"pending", "processing", "completed"}:
        orders = orders.filter(status=status_filter)
    else:
        status_filter = ""

    counts = {
        "all": GiftOrder.objects.count(),
        "pending": GiftOrder.objects.filter(status="pending").count(),
        "processing": GiftOrder.objects.filter(status="processing").count(),
        "completed": GiftOrder.objects.filter(status="completed").count(),
    }

    try:
        open_order = int(request.GET.get("open", "0"))
    except (TypeError, ValueError):
        open_order = 0

    return render(request, "finance/gift_orders.html", {
        "orders": orders,
        "counts": counts,
        "status_filter": status_filter,
        "open_order": open_order,
    })


@staff_member_required
@require_POST
def gift_order_update(request, pk):
    """Save the tracking link or move an order Processing / Completed."""
    from django.shortcuts import get_object_or_404
    from django.urls import reverse

    from gifts.models import GiftOrder

    order = get_object_or_404(GiftOrder, pk=pk)
    action = request.POST.get("action", "")

    if action == "save_tracking":
        # Accept anything: tracking number, full link, or plain text.
        link = (request.POST.get("tracking_link") or "").strip()
        if len(link) > 500:
            messages.error(request, "That tracking entry is too long (500 characters max).")
        else:
            order.tracking_link = link
            order.save(update_fields=["tracking_link", "updated_at"])
            if link:
                messages.success(request, f"Tracking saved for order {order.order_id}.")
            else:
                messages.success(request, f"Tracking cleared for order {order.order_id}.")

    elif action == "processing":
        if order.can_mark_processing():
            order.status = "processing"
            order.save(update_fields=["status", "updated_at"])
            messages.success(request, f"Order {order.order_id} is now Processing.")
        else:
            messages.warning(
                request,
                f"Order {order.order_id} cannot move to Processing from "
                f"'{order.get_status_display()}'.",
            )

    elif action == "completed":
        if order.can_mark_completed():
            order.status = "completed"
            order.save(update_fields=["status", "updated_at"])
            messages.success(request, f"Order {order.order_id} is now Completed.")
        else:
            messages.warning(request, f"Order {order.order_id} is already Completed.")

    else:
        messages.error(request, "Unknown action.")

    base = reverse("finance_gift_orders")
    return redirect(f"{base}?open={order.pk}#order-{order.pk}")


# ---------------------------------------------------------------------------
# Gift order photos: download every customer picture of one order as a ZIP
# ---------------------------------------------------------------------------

@staff_member_required
def gift_order_images_download(request, pk):
    """Bundle all customer photos of a gift order into one ZIP download."""
    import io
    import os
    import zipfile

    import requests
    from django.http import HttpResponse
    from django.shortcuts import get_object_or_404
    from django.urls import reverse

    from gifts.models import GiftOrder

    order = get_object_or_404(GiftOrder, pk=pk)
    buffer = io.BytesIO()
    added = 0
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for img in order.images.all():
            data = None
            # Local storage first (dev / disk setups).
            try:
                img.image.open("rb")
                data = img.image.read()
                img.image.close()
            except Exception:
                data = None
            # Remote storage fallback (e.g. Cloudinary): fetch the public URL.
            if not data:
                try:
                    resp = requests.get(img.image.url, timeout=30)
                    if resp.status_code == 200:
                        data = resp.content
                except Exception:
                    data = None
            if not data:
                continue
            ext = os.path.splitext(img.image.name or "")[1] or ".jpg"
            added += 1
            zf.writestr(f"{order.order_id}_photo_{added}{ext}", data)

    if added == 0:
        messages.error(request, f"No photos could be downloaded for order {order.order_id}.")
        base = reverse("finance_gift_orders")
        return redirect(f"{base}?open={order.pk}#order-{order.pk}")

    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{order.order_id}-photos.zip"'
    return response


# ---------------------------------------------------------------------------
# Gift order photos: download each customer picture as an image file
# ---------------------------------------------------------------------------

@staff_member_required
def gift_order_photo_download(request, pk, index):
    """Download one customer photo of a gift order as an image file."""
    import os

    import requests
    from django.http import Http404, HttpResponse
    from django.shortcuts import get_object_or_404

    from gifts.models import GiftOrder

    order = get_object_or_404(GiftOrder, pk=pk)
    images = list(order.images.all())
    if index < 0 or index >= len(images):
        raise Http404("Photo not found.")
    img = images[index]

    data = None
    # Local storage first (dev / disk setups).
    try:
        img.image.open("rb")
        data = img.image.read()
        img.image.close()
    except Exception:
        data = None
    # Remote storage fallback (e.g. Cloudinary): fetch the public URL.
    if not data:
        try:
            resp = requests.get(img.image.url, timeout=30)
            if resp.status_code == 200:
                data = resp.content
        except Exception:
            data = None
    if not data:
        raise Http404("Photo could not be downloaded.")

    ext = (os.path.splitext(img.image.name or "")[1] or ".jpg").lower()
    content_types = {
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    content_type = content_types.get(ext, "image/jpeg")
    filename = f"{order.order_id}_photo_{index + 1}{ext}"
    response = HttpResponse(data, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
