from django.contrib import admin
from django.utils.html import format_html

from .models import BoostFunding, LogBatch, SMSRecharge


@admin.register(SMSRecharge)
class SMSRechargeAdmin(admin.ModelAdmin):
    list_display = ("created_at", "provider_badge", "amount", "note")
    list_filter = ("server", "created_at")
    search_fields = ("note",)
    date_hierarchy = "created_at"

    @admin.display(description="Provider")
    def provider_badge(self, obj):
        color = "#17a2b8" if obj.server == "server1" else "#e83e8c"
        return format_html(
            '<strong style="color:{}">{}</strong>',
            color, obj.get_server_display(),
        )


@admin.register(BoostFunding)
class BoostFundingAdmin(admin.ModelAdmin):
    list_display = ("created_at", "amount", "note")
    search_fields = ("note",)
    date_hierarchy = "created_at"


@admin.register(LogBatch)
class LogBatchAdmin(admin.ModelAdmin):
    list_display = ("created_at", "product", "quantity", "cost", "status_badge", "note")
    list_editable = ("cost",)
    list_filter = ("status", "product__category", "created_at")
    search_fields = ("product__title", "note")
    ordering = ("-created_at",)
    readonly_fields = ("status", "confirmed_at")

    @admin.display(description="Status")
    def status_badge(self, obj):
        if obj.status == "confirmed":
            return format_html('<span style="color:#28a745;font-weight:bold">CONFIRMED</span>')
        return format_html('<span style="color:#ffc107;font-weight:bold">PENDING</span>')
