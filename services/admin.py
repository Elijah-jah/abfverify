from django.contrib import admin
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "provider_id",
        "status",
        "display_order",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "display_order",
        "name",
    )