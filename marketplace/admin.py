from django.contrib import admin

from .models import (
    LogCategory,
    LogSubCategory,
    LogProduct,
    LogItem,
    LogPurchase,
    LogOrderCounter,
)


@admin.register(LogCategory)
class LogCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order", "description")
    search_fields = ("name",)
    ordering = ("display_order", "name")


@admin.register(LogSubCategory)
class LogSubCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    list_filter = ("category",)
    search_fields = ("name", "category__name")


@admin.register(LogProduct)
class LogProductAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "sub_category", "price", "stock_display")
    list_filter = ("category", "sub_category")
    search_fields = ("title", "description")
    ordering = ("-created_at",)

    @admin.display(description="Stock")
    def stock_display(self, obj):
        return obj.in_stock


@admin.register(LogItem)
class LogItemAdmin(admin.ModelAdmin):
    list_display = ("uid", "product", "status", "created_at")
    list_filter = ("status", "product__category")
    search_fields = ("uid", "product__title")
    ordering = ("-created_at",)


@admin.register(LogPurchase)
class LogPurchaseAdmin(admin.ModelAdmin):
    list_display = ("order_id", "user", "product_title", "uid", "price", "created_at")
    search_fields = ("order_id", "product_title", "uid", "user__email")
    ordering = ("-created_at",)
    readonly_fields = ("order_id",)


@admin.register(LogOrderCounter)
class LogOrderCounterAdmin(admin.ModelAdmin):
    list_display = ("last_number",)