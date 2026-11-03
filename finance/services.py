from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import (
    Case, CharField, Count, F, Max, Min, Q, Sum, Value, When,
)
from django.db.models.functions import TruncDate
from django.utils import timezone

from boost.models import BoostOrder
from marketplace.models import LogItem, LogProduct, LogPurchase
from orders.models import Order
from wallet.models import Transaction

from .models import BoostFunding, LogBatch, SMSRecharge


# Completed normal orders plus status names used by some legacy datasets.
SMS_SUCCESS_STATUSES = (
    "completed",
    "received",
    "complete",
    "success",
    "successful",
)
SMS_EXCLUDED_STATUSES = (
    "cancelled",
    "canceled",
    "expired",
    "failed",
    "refunded",
)
BOOST_SUCCESS_STATUSES = ("Completed", "Partial")

# Recognize both current provider names and legacy server labels.
INSTANTNUMS_PROVIDER = (
    Q(provider__icontains="instantnums")
    | Q(provider__iexact="server1")
    | Q(provider__iexact="server 1")
    | Q(provider__iexact="server_1")
)
DAISYSMS_PROVIDER = (
    Q(provider__icontains="daisy")
    | Q(provider__iexact="server2")
    | Q(provider__iexact="server 2")
    | Q(provider__iexact="server_2")
)

RANGE_OPTIONS = [
    {"key": "all", "label": "All Time"},
    {"key": "today", "label": "Today"},
    {"key": "yesterday", "label": "Yesterday"},
    {"key": "last_3_days", "label": "Last 3 Days"},
    {"key": "last_4_days", "label": "Last 4 Days"},
    {"key": "last_5_days", "label": "Last 5 Days"},
    {"key": "last_6_days", "label": "Last 6 Days"},
    {"key": "last_week", "label": "Last Week (7 Days)"},
    {"key": "last_2_weeks", "label": "Last 2 Weeks (14 Days)"},
    {"key": "last_3_weeks", "label": "Last 3 Weeks (21 Days)"},
    {"key": "last_4_weeks", "label": "Last 4 Weeks (28 Days)"},
    {"key": "last_month", "label": "Last Month (30 Days)"},
    {"key": "last_2_months", "label": "Last 2 Months (60 Days)"},
]

RANGE_DAYS = {
    "last_3_days": 3,
    "last_4_days": 4,
    "last_5_days": 5,
    "last_6_days": 6,
    "last_week": 7,
    "last_2_weeks": 14,
    "last_3_weeks": 21,
    "last_4_weeks": 28,
    "last_month": 30,
    "last_2_months": 60,
}


def _sum(queryset, field):
    """Sum a field and always return a Decimal zero instead of None."""
    return queryset.aggregate(total=Sum(field))["total"] or Decimal("0.00")


def _q(value):
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _between(queryset, start=None, end=None):
    if start is not None:
        queryset = queryset.filter(created_at__gte=start)
    if end is not None:
        queryset = queryset.filter(created_at__lt=end)
    return queryset


def _tracked_sms_orders():
    """Return fulfilled SMS orders, including legacy delivered orders.

    Normal records are recognized by status. A legacy record with an incorrect
    pending/waiting status is still included when its stored OTP, full SMS, or
    delivery timestamp proves that the order was fulfilled. Explicitly cancelled,
    expired, failed, or refunded orders are never recovered through that fallback.
    """
    has_code = ~Q(sms_code__isnull=True) & ~Q(sms_code="")
    has_message = ~Q(full_sms__isnull=True) & ~Q(full_sms="")
    delivered_evidence = (
        Q(sms_received_at__isnull=False) | has_code | has_message
    )
    return Order.objects.filter(
        Q(status__in=SMS_SUCCESS_STATUSES)
        | (
            delivered_evidence
            & ~Q(status__in=SMS_EXCLUDED_STATUSES)
        )
    )


def _other_sms_orders(queryset):
    """Keep unusual legacy provider names visible instead of dropping them."""
    return queryset.exclude(INSTANTNUMS_PROVIDER).exclude(DAISYSMS_PROVIDER)


def _sales_summary(start=None, end=None):
    """Gross sales, separated by channel, for an optional local-time range."""
    sms_orders = _between(_tracked_sms_orders(), start, end)
    log_purchases = _between(LogPurchase.objects.all(), start, end)
    boost_orders = _between(
        BoostOrder.objects.filter(status__in=BOOST_SUCCESS_STATUSES), start, end
    )

    instantnums_orders = sms_orders.filter(INSTANTNUMS_PROVIDER)
    daisysms_orders = sms_orders.filter(DAISYSMS_PROVIDER)
    other_sms_orders = _other_sms_orders(sms_orders)

    instantnums = _sum(instantnums_orders, "price")
    daisysms = _sum(daisysms_orders, "price")
    other_sms = _sum(other_sms_orders, "price")
    sms_revenue = _sum(sms_orders, "price")
    logs_revenue = _sum(log_purchases, "price")
    boost_revenue = _sum(boost_orders, "price")

    return {
        "total": _q(sms_revenue + logs_revenue + boost_revenue),
        "sms": _q(sms_revenue),
        "instantnums": _q(instantnums),
        "daisysms": _q(daisysms),
        "other_sms": _q(other_sms),
        "logs": _q(logs_revenue),
        "boost": _q(boost_revenue),
        "record_count": (
            sms_orders.count() + log_purchases.count() + boost_orders.count()
        ),
        "sms_count": sms_orders.count(),
        "instantnums_count": instantnums_orders.count(),
        "daisysms_count": daisysms_orders.count(),
        "other_sms_count": other_sms_orders.count(),
        "logs_count": log_purchases.count(),
        "boost_count": boost_orders.count(),
    }


def _successful_deposits(start=None, end=None):
    deposits = Transaction.objects.filter(
        transaction_type="deposit",
        status="successful",
    )
    return _sum(_between(deposits, start, end), "amount")


def _day_start(value):
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def _first_historical_day(fallback):
    """Find the oldest existing business record for the All Time report."""
    earliest_values = []
    for model in (Order, LogPurchase, BoostOrder, Transaction):
        earliest = model.objects.aggregate(value=Min("created_at"))["value"]
        if earliest is not None:
            earliest_values.append(earliest)

    if not earliest_values:
        return fallback
    return _day_start(timezone.localtime(min(earliest_values)))


def _range_bounds(range_key):
    """Return start/end datetimes. Rolling ranges include today."""
    now = timezone.localtime()
    today = _day_start(now)

    if range_key == "all":
        return _first_historical_day(today), now
    if range_key == "yesterday":
        return today - timedelta(days=1), today
    if range_key in RANGE_DAYS:
        return today - timedelta(days=RANGE_DAYS[range_key] - 1), now
    return today, now


def _daily_totals(queryset, amount_field, start, end):
    rows = (
        _between(queryset, start, end)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Sum(amount_field))
        .order_by("day")
    )
    return {row["day"]: _q(row["total"] or 0) for row in rows}


def get_analytics_context(range_key="all"):
    valid_keys = {option["key"] for option in RANGE_OPTIONS}
    if range_key not in valid_keys:
        range_key = "all"

    start, end = _range_bounds(range_key)
    summary = _sales_summary(start, end)
    deposits = _successful_deposits(start, end)

    sms_orders = _tracked_sms_orders()
    instantnums_orders = sms_orders.filter(INSTANTNUMS_PROVIDER)
    daisysms_orders = sms_orders.filter(DAISYSMS_PROVIDER)
    other_sms_orders = _other_sms_orders(sms_orders)
    log_purchases = LogPurchase.objects.all()
    boost_orders = BoostOrder.objects.filter(status__in=BOOST_SUCCESS_STATUSES)

    daily_maps = {
        "instantnums": _daily_totals(
            instantnums_orders, "price", start, end,
        ),
        "daisysms": _daily_totals(
            daisysms_orders, "price", start, end,
        ),
        "other_sms": _daily_totals(
            other_sms_orders, "price", start, end,
        ),
        "logs": _daily_totals(log_purchases, "price", start, end),
        "boost": _daily_totals(boost_orders, "price", start, end),
    }

    # End is exclusive for Yesterday, so subtract one second for its chart date.
    final_day = timezone.localtime(end - timedelta(seconds=1)).date()
    first_day = timezone.localtime(start).date()
    day_count = max(1, (final_day - first_day).days + 1)

    chart_rows = []
    for offset in range(day_count):
        day = first_day + timedelta(days=offset)
        values = {
            source: source_rows.get(day, Decimal("0.00"))
            for source, source_rows in daily_maps.items()
        }
        total = sum(values.values(), Decimal("0.00"))
        chart_rows.append({
            "day": day,
            "label": day.strftime("%d %b"),
            "full_label": day.strftime("%A, %d %B %Y"),
            "total": _q(total),
            **values,
        })

    return {
        "analytics": summary,
        "analytics_deposits": _q(deposits),
        "total_users": get_user_model().objects.count(),
        "range_key": range_key,
        "range_label": next(
            option["label"] for option in RANGE_OPTIONS
            if option["key"] == range_key
        ),
        "range_options": RANGE_OPTIONS,
        "range_start": start,
        "range_end": end,
        "chart_rows": chart_rows,
        "chart_labels": [row["full_label"] for row in chart_rows],
        "chart_values": [float(row["total"]) for row in chart_rows],
    }


def get_dashboard_stats():
    sales = _sales_summary()

    # ============ SMS PROVIDER FUNDING ============
    instantnums_funding = _sum(
        SMSRecharge.objects.filter(server="server1"), "amount"
    )
    daisysms_funding = _sum(
        SMSRecharge.objects.filter(server="server2"), "amount"
    )
    sms_costs = instantnums_funding + daisysms_funding
    sms_profit = sales["sms"] - sms_costs

    # ============ LOGS ============
    logs_investment = _sum(
        LogBatch.objects.filter(status="confirmed"), "cost"
    )
    logs_profit = sales["logs"] - logs_investment
    pending_batches = LogBatch.objects.filter(
        status="pending"
    ).select_related("product")

    # Include every product, including products whose available stock is zero.
    products = (
        LogProduct.objects
        .annotate(
            units=Count(
                "items",
                filter=Q(items__status="available"),
            )
        )
        .order_by("title")
    )
    stock_value = Decimal("0.00")
    stock_units = 0
    stock_by_product = []
    for product in products:
        units = product.units
        line_value = _q(product.price) * units
        stock_value += line_value
        stock_units += units
        stock_by_product.append({
            "title": product.title,
            "units": units,
            "value": _q(line_value),
        })

    # Old sold items without a LogPurchase cannot supply an exact buyer, price,
    # or sale timestamp. Surface them rather than inventing financial records.
    legacy_sold_without_purchase = LogItem.objects.filter(
        status="sold",
        purchase__isnull=True,
    ).count()

    # ============ BOOST ============
    boost_funding = _sum(BoostFunding.objects.all(), "amount")
    boost_profit = sales["boost"] - boost_funding

    # ============ USERS + DEPOSITS ============
    total_users = get_user_model().objects.count()
    total_deposits = _successful_deposits()

    # ============ GRAND TOTALS ============
    total_costs = sms_costs + logs_investment + boost_funding
    grand_profit = sales["total"] - total_costs

    # Current calendar periods, all based on each record's created_at value.
    now = timezone.localtime()
    today = _day_start(now)
    period_starts = {
        "today": today,
        "week": today - timedelta(days=today.weekday()),
        "month": today.replace(day=1),
        "year": today.replace(month=1, day=1),
    }
    periods = {
        key: _sales_summary(start, now)
        for key, start in period_starts.items()
    }

    return {
        "sms": {
            "revenue": sales["sms"],
            "instantnums_revenue": sales["instantnums"],
            "daisysms_revenue": sales["daisysms"],
            "other_sms_revenue": sales["other_sms"],
            "orders": sales["sms_count"],
            "instantnums_orders": sales["instantnums_count"],
            "daisysms_orders": sales["daisysms_count"],
            "other_sms_orders": sales["other_sms_count"],
            "instantnums_funding": _q(instantnums_funding),
            "daisysms_funding": _q(daisysms_funding),
            "costs": _q(sms_costs),
            "profit": _q(sms_profit),
        },
        "logs": {
            "revenue": sales["logs"],
            "purchases": sales["logs_count"],
            "investment": _q(logs_investment),
            "stock_value": _q(stock_value),
            "stock_units": stock_units,
            "profit": _q(logs_profit),
        },
        "boost": {
            "revenue": sales["boost"],
            "orders": sales["boost_count"],
            "funding": _q(boost_funding),
            "profit": _q(boost_profit),
        },
        "totals": {
            "users": total_users,
            "deposits": _q(total_deposits),
            "revenue": sales["total"],
            "records": sales["record_count"],
            "costs": _q(total_costs),
            "profit": _q(grand_profit),
        },
        "coverage": {
            "legacy_sold_without_purchase": legacy_sold_without_purchase,
        },
        "periods": periods,
        "pending_batches": pending_batches,
        "stock_by_product": stock_by_product,
    }


def get_daily_sales_inventory():
    """Group today's log, SMS, and boost sales for the inventory page.

    Logs use their purchase snapshots, SMS uses the same fulfilled-order rules as
    finance analytics, and boosts include every paid order not marked cancelled.
    No customer credentials, phone numbers, usernames, or boost links are queried.
    """
    today = _day_start(timezone.localtime())
    tomorrow = today + timedelta(days=1)

    log_sales = _between(LogPurchase.objects.all(), today, tomorrow)
    log_rows = list(
        log_sales
        .values("product_title")
        .annotate(
            units_sold=Count("id"),
            revenue=Sum("price"),
            last_sold=Max("created_at"),
        )
        .order_by("-units_sold", "product_title")
    )

    sms_sales = _between(_tracked_sms_orders(), today, tomorrow)
    sms_rows = list(
        sms_sales
        .annotate(
            provider_group=Case(
                When(
                    INSTANTNUMS_PROVIDER,
                    then=Value("Server 1 — InstantNums"),
                ),
                When(
                    DAISYSMS_PROVIDER,
                    then=Value("Server 2 — DaisySMS"),
                ),
                default=F("provider"),
                output_field=CharField(),
            )
        )
        .values("country__name", "service__name", "provider_group")
        .annotate(
            numbers_sold=Count("id"),
            revenue=Sum("price"),
            last_sold=Max("created_at"),
        )
        .order_by("country__name", "service__name", "provider_group")
    )

    # A boost is paid when accepted by the provider. Include open orders at once,
    # but omit cancelled orders from this operational sales inventory.
    boost_sales = _between(
        BoostOrder.objects.exclude(status__iexact="Canceled")
        .exclude(status__iexact="Cancelled"),
        today,
        tomorrow,
    )
    boost_rows = list(
        boost_sales
        .values("service__category", "service__name")
        .annotate(
            orders=Count("id"),
            units=Sum("quantity"),
            order_value=Sum("price"),
            fulfilled_orders=Count(
                "id", filter=Q(status__in=BOOST_SUCCESS_STATUSES)
            ),
            open_orders=Count(
                "id",
                filter=Q(status__in=("Pending", "Processing", "In progress")),
            ),
            last_ordered=Max("created_at"),
        )
        .order_by("service__category", "service__name")
    )

    totals = {
        "logs_units": sum(row["units_sold"] for row in log_rows),
        "logs_revenue": _q(_sum(log_sales, "price")),
        "sms_numbers": sum(row["numbers_sold"] for row in sms_rows),
        "sms_revenue": _q(_sum(sms_sales, "price")),
        "boost_orders": sum(row["orders"] for row in boost_rows),
        "boost_units": sum((row["units"] or 0) for row in boost_rows),
        "boost_value": _q(_sum(boost_sales, "price")),
    }
    totals["sales_value"] = _q(
        totals["logs_revenue"]
        + totals["sms_revenue"]
        + totals["boost_value"]
    )

    return {
        "inventory_date": today.date(),
        "inventory_generated_at": timezone.localtime(),
        "log_rows": log_rows,
        "sms_rows": sms_rows,
        "boost_rows": boost_rows,
        "inventory_totals": totals,
    }