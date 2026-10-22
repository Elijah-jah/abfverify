from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from marketplace.models import LogProduct

from .models import BoostFunding, LogBatch, SMSRecharge
from .services import get_dashboard_stats


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

    # Recompute quantity server-side — never trust the form
    untracked = [u for u in _get_untracked_restock() if u["product"].id == product.id]
    if not untracked:
        messages.info(request, "This upload is already recorded.")
        return redirect("finance_dashboard")

    quantity = untracked[0]["quantity"]
    LogBatch.objects.create(product=product, quantity=quantity, cost=cost)
    messages.success(request, f"✅ Recorded restock — {product.title} ×{quantity} at ₦{cost:,.2f}")
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
    messages.success(request, f"✅ Recharge recorded — {label}: ₦{amount:,.2f}")
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
    messages.success(request, f"✅ Boost funding recorded — ₦{amount:,.2f}")
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
            messages.error(request, "Cost must be a valid amount — or leave it empty to keep the batch PENDING.")
            return redirect("finance_dashboard")

    batch = LogBatch.objects.create(
        product=product, quantity=quantity, cost=cost, note=note
    )
    if batch.status == "confirmed":
        messages.success(request, f"✅ Restock confirmed — {product.title} ×{quantity} at ₦{cost:,.2f}")
    else:
        messages.warning(request, f"⏳ Restock added as PENDING — {product.title} ×{quantity}. Enter the cost later to confirm it.")
    return redirect("finance_dashboard")
