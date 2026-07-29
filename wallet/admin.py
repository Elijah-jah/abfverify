from django.contrib import admin
from django.db.models import Sum
from .models import Wallet, Transaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "balance",
        "updated_at",
    )

    search_fields = (
        "user__username",
        "user__email",
    )

    ordering = (
        "-updated_at",
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "amount",
        "transaction_type",
        "status",
        "reference",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "reference",
    )

    list_filter = (
        "transaction_type",
        "status",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "reference",
        "created_at",
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        successful = Transaction.objects.filter(
            transaction_type="deposit",
            status="successful"
        )

        extra_context["total_deposits"] = successful.count()

        extra_context["total_amount"] = (
            successful.aggregate(total=Sum("amount"))["total"] or 0
        )

        return super().changelist_view(request, extra_context=extra_context)