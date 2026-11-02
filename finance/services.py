from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from boost.models import BoostOrder
from marketplace.models import LogItem, LogProduct, LogPurchase
from orders.models import Order
from wallet.models import Transaction

from .models import BoostFunding, LogBatch, SMSRecharge


SMS_SUCCESS_STATUSES = ("completed", "received")
BOOST_SUCCESS_STATUSES = ("Completed", "Partial")

RANGE_OPTIONS = [
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


def _sales_summary(start=None, end=None):
    """Gross sales, separated by channel, for an optional local-time range."""
    sms_orders = _between(
        Order.objects.filter(status__in=SMS_SUCCESS_STATUSES), start, end
    )
    log_purchases = _between(LogPurchase.objects.all(), start, end)
    boost_orders = _between(
        BoostOrder.objects.filter(status__in=BOOST_SUCCESS_STATUSES), start, end
    )

    instantnums = _sum(
        sms_orders.filter(provider__icontains="instantnums"), "price"
    )
    daisysms = _sum(
        sms_orders.filter(provider__icontains="daisy"), "price"
    )
    sms_revenue = _sum(sms_orders, "price")
    logs_revenue = _sum(log_purchases, "price")
    boost_revenue = _sum(boost_orders, "price")

    return {
        "total": _q(sms_revenue + logs_revenue + boost_revenue),
        "sms": _q(sms_revenue),
        "instantnums": _q(instantnums),
        "daisysms": _q(daisysms),
        "logs": _q(logs_revenue),
        "boost": _q(boost_revenue),
    }


def _successful_deposits(start=None, end=None):
    deposits = Transaction.objects.filter(
        transaction_type="deposit",
        status="successful",
    )
    return _sum(_between(deposits, start, end), "amount")


def _day_start(value):
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def _range_bounds(range_key):
    """Return start/end datetimes. Rolling ranges include today."""
    now = timezone.localtime()
    today = _day_start(now)

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


def get_analytics_context(range_key="today"):
    valid_keys = {option["key"] for option in RANGE_OPTIONS}
    if range_key not in valid_keys:
        range_key = "today"

    start, end = _range_bounds(range_key)
    summary = _sales_summary(start, end)
    deposits = _successful_deposits(start, end)

    sms_orders = Order.objects.filter(status__in=SMS_SUCCESS_STATUSES)
    log_purchases = LogPurchase.objects.all()
    boost_orders = BoostOrder.objects.filter(status__in=BOOST_SUCCESS_STATUSES)

    daily_maps = {
        "instantnums": _daily_totals(
            sms_orders.filter(provider__icontains="instantnums"),
            "price", start, end,
        ),
        "daisysms": _daily_totals(
            sms_orders.filter(provider__icontains="daisy"),
            "price", start, end,
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
            "instantnums_funding": _q(instantnums_funding),
            "daisysms_funding": _q(daisysms_funding),
            "costs": _q(sms_costs),
            "profit": _q(sms_profit),
        },
        "logs": {
            "revenue": sales["logs"],
            "investment": _q(logs_investment),
            "stock_value": _q(stock_value),
            "stock_units": stock_units,
            "profit": _q(logs_profit),
        },
        "boost": {
            "revenue": sales["boost"],
            "funding": _q(boost_funding),
            "profit": _q(boost_profit),
        },
        "totals": {
            "users": total_users,
            "deposits": _q(total_deposits),
            "revenue": sales["total"],
            "costs": _q(total_costs),
            "profit": _q(grand_profit),
        },
        "periods": periods,
        "pending_batches": pending_batches,
        "stock_by_product": stock_by_product,
    }