from django.contrib import admin

from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("__str__", "updated_at")
    readonly_fields = ("updated_at", "logo_preview")
    fields = ("logo", "logo_preview", "updated_at")

    def has_add_permission(self, request):
        # Only one settings row is ever allowed.
        if SiteSettings.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Current logo")
    def logo_preview(self, obj):
        if obj and obj.logo:
            from django.utils.html import format_html

            return format_html(
                '<img src="{}" style="max-height:80px;max-width:220px;'
                'border-radius:8px;background:#f3f5f8;padding:6px;" alt="logo" />',
                obj.logo.url,
            )
        return "No logo uploaded yet — the default file logo is used."
