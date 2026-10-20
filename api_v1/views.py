import logging
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from countries.models import Country
from services.models import Service
from wallet.models import Wallet, Transaction
from orders.models import Order
from providers.factory import get_provider
from pricing.models import Pricing
logger = logging.getLogger(__name__)
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt
@require_POST
def instantnums_webhook(request):
    """InstantNums pushes received SMS codes here.

    Phase 1: log the raw payload so we can see InstantNums' exact field
    names, and attempt a best-guess match. After we confirm the payload
    shape, the parsing below gets tightened."""
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'ok': False, 'error': 'bad json'}, status=400)

    logger.info('WEBHOOK PAYLOAD: %s', payload)   # <-- so we can see the shape

    # --- best-guess field extraction (to be confirmed against real payload) ---
    number = (payload.get('number') or payload.get('phone')
              or payload.get('phone_number') or payload.get('msisdn'))
    code = (payload.get('code') or payload.get('sms_code')
            or payload.get('otp') or payload.get('text') or payload.get('sms'))
    full = payload.get('full_sms') or payload.get('message') or payload.get('text') or ''

    if not number or not code:
        return JsonResponse({'ok': False, 'error': 'unrecognized payload'}, status=400)

    order = (Order.objects
             .filter(phone_number__icontains=str(number)[-10:],  # match last 10 digits
                     status='waiting')
             .order_by('-id')
             .first())
    if not order:
        return JsonResponse({'ok': False, 'error': 'no matching order'}, status=404)

    # Same atomic pay-on-delivery logic as check_sms
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        if locked.status != 'waiting':
            return JsonResponse({'ok': True, 'note': 'already handled'})
        wallet = Wallet.objects.select_for_update().get(user=locked.user)
        if wallet.balance < locked.price:
            return JsonResponse({'ok': False, 'error': 'insufficient funds'}, status=400)
        wallet.balance -= locked.price
        wallet.save(update_fields=['balance'])
        Transaction.objects.create(
            user=locked.user, amount=locked.price,
            transaction_type='payment', status='successful',
            description=f'Payment for {locked.service.name} number ({locked.phone_number})')
        locked.sms_code = str(code)
        locked.full_sms = str(full)
        locked.sms_received_at = timezone.now()
        locked.status = 'received'
        locked.save(update_fields=['sms_code', 'full_sms', 'sms_received_at', 'status', 'updated_at'])

    return JsonResponse({'ok': True})


@login_required
def get_countries(request):
    """Return countries for selected server."""
    server = request.GET.get("server", "server2")
    
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
    server = request.GET.get("server", "server2")
    
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
    """Return cached price from database. Never hits the provider."""
    country_id = request.GET.get("country")
    service_id = request.GET.get("service")

    if not country_id or not service_id:
        return JsonResponse({
            "success": False,
            "price": 0,
            "error": "Missing country or service",
        })

    try:
        pricing = Pricing.objects.get(
            country_id=country_id,
            service_id=service_id,
            status="active",
        )
        return JsonResponse({
            "success": True,
            "selling_price": str(pricing.selling_price),
            "provider_cost": str(pricing.provider_cost),
        })
    except Pricing.DoesNotExist:
        return JsonResponse({
            "success": False,
            "price": 0,
            "error": "Price not available for this service yet",
        })
    except Exception as e:
        logger.error("Get price error: %s", e)
        return JsonResponse({
            "success": False,
            "price": 0,
            "error": "Price temporarily unavailable",
        })