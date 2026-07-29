import logging
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from countries.models import Country
from services.models import Service
from pricing.services import PricingService
from wallet.models import Wallet, Transaction
from orders.models import Order
from providers.factory import get_provider
from pricing.models import Pricing

logger = logging.getLogger(__name__)


@login_required
def get_countries(request):
    """Return countries for selected server."""
    server = request.GET.get("server", "server3")
    
    countries = Country.objects.filter(
        status="active",
        server=server,
    ).values("id", "name", "iso_code", "phone_code").order_by("display_order", "name")
    
    return JsonResponse({
        "success": True,
        "countries": list(countries),
    })


@login_required
def get_services(request):
    """Return services for selected server."""
    server = request.GET.get("server", "server3")
    
    services = Service.objects.filter(
        status="active",
        server=server,
    ).values("id", "name", "provider_id", "code").order_by("display_order", "name")
    
    return JsonResponse({
        "success": True,
        "services": list(services),
    })


@login_required
def check_sms(request):
    order_id = request.GET.get("order_id")
    
    if not order_id:
        return JsonResponse({
            "success": False,
            "status": "error",
            "message": "Order ID required.",
        })

    try:
        order = Order.objects.get(
            id=order_id,
            user=request.user,
        )
    except Order.DoesNotExist:
        return JsonResponse({
            "success": False,
            "status": "no_order",
            "message": "Order not found.",
        })

    # If order is expired or cancelled, hide container
    if order.status in ("expired", "cancelled"):
        return JsonResponse({
            "success": True,
            "status": "done",
            "message": "Order finished.",
        })

    # If SMS already received and wallet deducted, show code and keep container visible
    if order.status == "received" and order.sms_code:
        return JsonResponse({
            "success": True,
            "status": "finished",
            "sms": order.sms_code,
            "full_sms": order.full_sms or "",
        })

    # If order is completed (timer ran out, no SMS), hide container
    if order.status == "completed":
        return JsonResponse({
            "success": True,
            "status": "done",
            "message": "Order expired.",
        })

    # If order is no longer waiting and no SMS, hide container
    if order.status != "waiting" and not order.sms_code:
        return JsonResponse({
            "success": False,
            "status": "no_order",
            "message": "Order is no longer active.",
        })

    # Get correct provider based on server stored in order
    provider = get_provider(server=order.provider)

    try:
        result = provider.check_sms(order.provider_order_id)
    except Exception as e:
        logger.warning("Provider check_sms failed for server %s: %s", order.provider, str(e))
        return JsonResponse({
            "success": False,
            "status": "provider_error",
            "message": "Provider unavailable.",
        })

    if result.get("status") == "finished":
        # SMS ARRIVED — DEDUCT WALLET NOW
        try:
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=request.user)
                
                # Check balance again (might have changed since order was created)
                if wallet.balance < order.price:
                    return JsonResponse({
                        "success": False,
                        "status": "insufficient_funds",
                        "message": "Insufficient wallet balance. Please add funds.",
                    })
                
                wallet.balance -= order.price
                wallet.save(update_fields=["balance"])

                # CREATE TRANSACTION RECORD FOR AUDIT TRAIL
                Transaction.objects.create(
                    user=request.user,
                    amount=order.price,
                    transaction_type="payment",
                    status="successful",
                    description=f"Payment for {order.service.name} number ({order.phone_number})"
                )

                # Update order to "received" so container stays visible
                order.sms_code = result.get("sms")
                order.full_sms = result.get("full_sms", "")
                order.sms_received_at = timezone.now()
                order.status = "received"
                order.save(update_fields=[
                    "sms_code", "full_sms", "sms_received_at", 
                    "status", "updated_at"
                ])

        except Exception as e:
            logger.exception("Payment deduction failed for order %s: %s", order.order_id, str(e))
            return JsonResponse({
                "success": False,
                "status": "payment_error",
                "message": "Failed to process payment. Please try again.",
            })

        return JsonResponse({
            "success": True,
            "status": "finished",
            "sms": order.sms_code,
            "full_sms": order.full_sms,
        })

    return JsonResponse({
        "success": True,
        "status": "waiting",
    })


@login_required
def get_price(request):
    country_id = request.GET.get("country")
    service_id = request.GET.get("service")
    server = request.GET.get("server", "server3")

    if not country_id or not service_id:
        return JsonResponse({
            "success": False,
            "price": 0,
            "error": "Missing country or service",
        })

    try:
        country = Country.objects.get(id=country_id)
        service = Service.objects.get(id=service_id)

        # === INSTANT: Use cached price from database ===
        try:
            pricing = Pricing.objects.get(
                country=country,
                service=service,
                status="active",
            )
            return JsonResponse({
                "success": True,
                "selling_price": str(pricing.selling_price),
                "provider_cost": str(pricing.provider_cost),
                "available": True,  # Price exists, so we assume available until stock check says otherwise
            })

        except Pricing.DoesNotExist:
            # === First time only: fetch live from InstantNums and cache it ===
            print(f"[InstantNums] No cached price for {service.name}/{country.name}, fetching live...")
            pricing = PricingService.update_price(
                country=country,
                service=service,
                server=server,
            )
            return JsonResponse({
                "success": True,
                "selling_price": str(pricing.selling_price),
                "provider_cost": str(pricing.provider_cost),
                "available": True,
            })

    except Exception as e:
        print(f"[InstantNums] Get price error: {e}")
        return JsonResponse({
            "success": False,
            "price": 0,
            "error": "Price temporarily unavailable",
        })


@login_required
def check_stock(request):
    country_id = request.GET.get("country")
    service_id = request.GET.get("service")
    server = request.GET.get("server", "server3")

    if not country_id or not service_id:
        return JsonResponse({
            "success": False,
            "available": 0,
            "error": "Missing country or service",
        })

    try:
        country = Country.objects.get(id=country_id)
        service = Service.objects.get(id=service_id)

        provider = get_provider(server=server)

        if server == "server2":
            service_identifier = service.code
            country_identifier = 187
        else:
            service_identifier = service.provider_id
            country_identifier = country.provider_id

        print(f"[InstantNums] Checking stock: service={service_identifier}, country={country_identifier}")

        result = provider.check_stock(
            service=service_identifier,
            country=country_identifier,
        )

        available = result.get("available", 0)
        print(f"[InstantNums] Stock result: {available} available")

        return JsonResponse({
            "success": True,
            "available": available,
        })

    except Exception as e:
        print(f"[InstantNums] Check stock error: {e}")
        # Return success=False so frontend knows it was an error, not actually 0 stock
        return JsonResponse({
            "success": False,
            "available": 0,
            "error": str(e),
        })