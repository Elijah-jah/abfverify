from django.contrib import admin
from .models import Pricing
from .models import PricingConfiguration


@admin.register(Pricing)
class PricingAdmin(admin.ModelAdmin):
    list_display = (
        "country",
        "service",
        "selling_price",
        "provider_cost",
        "is_available",
        "status",
    )

    list_filter = (
        "country",
        "status",
        "is_available",
    )

    search_fields = (
        "country__name",
        "service__name",
    )




@admin.register(PricingConfiguration)
class PricingConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "exchange_rate",
        "fixed_profit",
        "updated_at",
    )