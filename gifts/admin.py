from django.contrib import admin
from django.utils.html import format_html

from .models import GiftCategory, GiftGroup, GiftOrder, GiftOrderImage


@admin.register(GiftCategory)
class GiftCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    search_fields = ("name",)


@admin.register(GiftGroup)
class GiftGroupAdmin(admin.ModelAdmin):
    list_display = (
        "image_preview", "name", "category", "price",
        "delivery_duration", "display_order", "is_active", "created_at",
    )
    list_filter = ("category", "is_active")
    list_editable = ("price", "delivery_duration", "display_order", "is_active")
    search_fields = ("name", "description", "category__name")

    @admin.display(description="Image")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:44px;height:44px;object-fit:cover;border-radius:8px;">',
                obj.image.url,
            )
        return "\u2014"


class GiftOrderImageInline(admin.TabularInline):
    model = GiftOrderImage
    extra = 0
    can_delete = False
    fields = ("image_preview", "image", "uploaded_at")
    readonly_fields = ("image_preview", "uploaded_at")

    @admin.display(description="Preview")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<a href="{0}" target="_blank" rel="noopener">'
                '<img src="{0}" style="width:64px;height:64px;object-fit:cover;'
                'border-radius:8px;border:1px solid #1c2942;"></a>',
                obj.image.url,
            )
        return "\u2014"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(GiftOrder)
class GiftOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_id", "group_name", "user", "price",
        "receiver_name", "status", "created_at",
    )
    list_select_related = ("user",)
    inlines = (GiftOrderImageInline,)
    list_filter = ("status", "category_name", "created_at")
    list_editable = ("status",)
    search_fields = (
        "order_id", "group_name", "user__username", "user__email",
        "sender_name", "receiver_name", "phone",
    )
    readonly_fields = (
        "order_id", "user", "group", "group_name", "category_name",
        "group_image_url", "price", "sender_name", "receiver_name",
        "address", "city", "state", "zip_code", "phone",
        "created_at", "updated_at",
    )
