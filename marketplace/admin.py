from django.contrib import admin
from .models import (
    LogCategory, LogSubCategory, LogProduct, LogItem,
    LogPurchase, LogOrderCounter
)


class LogItemInline(admin.TabularInline):
    model = LogItem
    extra = 1
    fields = ["username", "password", "status"]


@admin.register(LogCategory)
class LogCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "icon", "display_order"]
    list_editable = ["display_order"]


@admin.register(LogSubCategory)
class LogSubCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "category"]
    list_filter = ["category"]


@admin.register(LogProduct)
class LogProductAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "sub_category", "price", "in_stock", "created_at"]
    list_filter = ["category", "sub_category", "created_at"]
    search_fields = ["title", "description"]
    inlines = [LogItemInline]


@admin.register(LogItem)
class LogItemAdmin(admin.ModelAdmin):
    list_display = ["product", "username", "status", "created_at"]
    list_filter = ["status", "product", "created_at"]
    search_fields = ["username", "product__title"]


@admin.register(LogPurchase)
class LogPurchaseAdmin(admin.ModelAdmin):
    list_display = ["order_id", "user", "product_title", "price", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["order_id", "product_title", "user__username"]
    readonly_fields = ["order_id", "created_at"]


@admin.register(LogOrderCounter)
class LogOrderCounterAdmin(admin.ModelAdmin):
    list_display = ["last_number"]