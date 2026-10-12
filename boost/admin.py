from django.contrib import admin

from .models import BoostService, BoostOrder, BoostSettings
from .providers import ReallySimpleSocial, ReallySimpleSocialError


@admin.register(BoostService)
class BoostServiceAdmin(admin.ModelAdmin):
    list_display = ("service_id", "name", "category", "rate", "min_order", "max_order", "is_active")
    list_filter = ("category", "is_active", "refill", "cancel")
    search_fields = ("name", "category", "service_id")
    list_per_page = 50
    actions = ["sync_from_api"]

    @admin.action(description="Sync services from ReallySimpleSocial (fetches ALL)")
    def sync_from_api(self, request, queryset):
        try:
            provider = ReallySimpleSocial()
            services = provider.get_services()
        except ReallySimpleSocialError as e:
            self.message_user(request, f"Sync failed: {e}", level="error")
            return

        created = updated = 0
        for s in services:
            defaults = {
                "name": s["name"],
                "category": s.get("category", ""),
                "service_type": s.get("type", ""),
                "rate": s["rate"],
                "min_order": s["min"],
                "max_order": s["max"],
                "refill": bool(s.get("refill")),
                "cancel": bool(s.get("cancel")),
            }

            # Import description only if the API returns one — otherwise
            # keep whatever is already saved (e.g. written manually in admin)
            desc = s.get("description") or s.get("desc")
            if desc:
                defaults["description"] = desc

            _, was_created = BoostService.objects.update_or_create(
                service_id=s["service"],
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.message_user(request, f"Sync complete: {created} new, {updated} updated.")


@admin.register(BoostOrder)
class BoostOrderAdmin(admin.ModelAdmin):
    list_display = ("provider_order_id", "user", "service", "quantity", "price", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("provider_order_id", "link", "user__username")
    readonly_fields = ("provider_order_id", "start_count", "remains")


@admin.register(BoostSettings)
class BoostSettingsAdmin(admin.ModelAdmin):
    list_display = ("exchange_rate", "profit_per_1000", "updated_at")

    def has_add_permission(self, request):
        return not BoostSettings.objects.exists()