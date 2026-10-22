from decimal import Decimal

from django.db.models import Count, Sum

from boost.models import BoostOrder
from marketplace.models import LogItem, LogPurchase
from orders.models import Order

from .models import BoostFunding, LogBatch, SMSRecharge


def _sum(qs, field):
    """Sum a field - never return None."""
    return qs.aggregate(total=Sum(field))["total"] or Decimal("0.00")


def _q(value):
    return Decimal(str(value)).quantize(Decimal("0.01"))


def get_dashboard_stats():
    # ============ SMS ============
    sms_orders = Order.objects.filter(status__in=["completed", "received"])
    sms_revenue = _sum(sms_orders, "price")

    instantnums_funding = _sum(SMSRecharge.objects.filter(server="server1"), "amount")
    daisysms_funding = _sum(SMSRecharge.objects.filter(server="server2"), "amount")
    sms_costs = instantnums_funding + daisysms_funding
    sms_profit = sms_revenue - sms_costs

    # ============ LOGS ============
    logs_revenue = _sum(LogPurchase.objects.all(), "price")
    logs_investment = _sum(LogBatch.objects.filter(status="confirmed"), "cost")
    logs_profit = logs_revenue - logs_investment

    pending_batches = LogBatch.objects.filter(status="pending").select_related("product")

    # Current stock value: available items grouped by product price
    stock_rows = (
        LogItem.objects.filter(status="available")
        .values("product__title", "product__price")
        .annotate(units=Count("id"))
    )
    stock_value = Decimal("0.00")
    stock_units = 0
    stock_by_product = []
    for row in stock_rows:
        line_value = _q(row["product__price"]) * row["units"]
        stock_value += line_value
        stock_units += row["units"]
        stock_by_product.append({
            "title": row["product__title"],
            "units": row["units"],
            "price": _q(row["product__price"]),
            "value": _q(line_value),
        })
    stock_by_product.sort(key=lambda x: x["value"], reverse=True)

    # ============ BOOST ============
    boost_revenue = _sum(BoostOrder.objects.all(), "price")
    boost_funding = _sum(BoostFunding.objects.all(), "amount")
    boost_profit = boost_revenue - boost_funding

    # ============ TOTALS ============
    total_revenue = sms_revenue + logs_revenue + boost_revenue
    total_costs = sms_costs + logs_investment + boost_funding
    grand_profit = sms_profit + logs_profit + boost_profit

    return {
        "sms": {
            "revenue": _q(sms_revenue),
            "instantnums_funding": _q(instantnums_funding),
            "daisysms_funding": _q(daisysms_funding),
            "costs": _q(sms_costs),
            "profit": _q(sms_profit),
        },
        "logs": {
            "revenue": _q(logs_revenue),
            "investment": _q(logs_investment),
            "stock_value": _q(stock_value),
            "stock_units": stock_units,
            "profit": _q(logs_profit),
        },
        "boost": {
            "revenue": _q(boost_revenue),
            "funding": _q(boost_funding),
            "profit": _q(boost_profit),
        },
        "totals": {
            "revenue": _q(total_revenue),
            "costs": _q(total_costs),
            "profit": _q(grand_profit),
        },
        "pending_batches": pending_batches,
        "stock_by_product": stock_by_product,
    }
