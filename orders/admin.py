from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "order_id",
        "user",
        "country",
        "service",
        "phone_number",
        "price",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "country",
        "service",
        "provider",
        "created_at",
    )

    search_fields = (
        "order_id",
        "user__username",
        "user__email",
        "phone_number",
        "provider_order_id",
    )

    readonly_fields = (
        "order_id",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 25

    fieldsets = (

        ("Order Information", {
            "fields": (
                "order_id",
                "user",
                "status",
            )
        }),

        ("Service Details", {
            "fields": (
                "country",
                "service",
                "phone_number",
                "provider",
                "provider_order_id",
            )
        }),

        ("Payment", {
            "fields": (
                "price",
            )
        }),

        ("SMS", {
            "fields": (
                "sms_code",
            )
        }),

        ("Dates", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )