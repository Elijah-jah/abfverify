from django.contrib import admin
from .models import Country


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "iso_code",
        "phone_code",
        "status",
        "display_order",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "name",
        "iso_code",
        "phone_code",
    )

    ordering = (
        "display_order",
        "name",
    )