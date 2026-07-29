from django.http import JsonResponse
from django.views.decorators.http import require_GET

from countries.models import Country
from services.models import Service
from .services import PricingService


@require_GET
def get_live_price(request):
    country_id = request.GET.get("country")
    service_id = request.GET.get("service")
    server = request.GET.get("server", "server3")  # ADD THIS

    if not country_id or not service_id:
        return JsonResponse(
            {
                "success": False,
                "message": "Country and service are required.",
            },
            status=400,
        )

    try:
        country = Country.objects.get(pk=country_id)
        service = Service.objects.get(pk=service_id)

        pricing = PricingService.update_price(
            country=country,
            service=service,
            server=server,  # ADD THIS
        )

        return JsonResponse(
            {
                "success": True,
                "selling_price": str(pricing.selling_price),
                "provider_cost": str(pricing.provider_cost),
                "available": pricing.is_available,
            }
        )

    except Country.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Country not found.",
            },
            status=404,
        )

    except Service.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Service not found.",
            },
            status=404,
        )

    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "message": str(e),
            },
            status=500,
        )