from django import forms
from django.contrib import admin

from .models import (
    RedeemCode,
    ReferralProfile,
    ReferralReward,
    generate_redeem_code,
)


class RedeemCodeAdminForm(forms.ModelForm):
    """Admin code generation: type your own code, or leave the code
    field blank and one is auto-generated for you. Set the amount,
    hit Save — the code is live and one-time use."""

    code = forms.CharField(
        required=False,
        max_length=32,
        help_text=(
            "Type any code you want (e.g. ABFVERIFY2026), or leave "
            "blank to auto-generate a random one."
        ),
    )

    class Meta:
        model = RedeemCode
        fields = ("code", "amount")

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip().upper()
        if not code:
            code = generate_redeem_code()
        if RedeemCode.objects.filter(code__iexact=code).exists():
            raise forms.ValidationError("This code already exists.")
        return code


@admin.register(RedeemCode)
class RedeemCodeAdmin(admin.ModelAdmin):
    form = RedeemCodeAdminForm

    list_display = (
        "code",
        "amount",
        "is_redeemed",
        "redeemed_by",
        "redeemed_at",
        "created_at",
    )
    list_filter = ("is_redeemed", "created_at")
    search_fields = ("code", "redeemed_by__username", "redeemed_by__email")
    ordering = ("-created_at",)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            # Existing codes are locked - one code, one amount, forever.
            return ("code", "amount", "is_redeemed", "redeemed_by", "redeemed_at", "created_at")
        return ("is_redeemed", "redeemed_by", "redeemed_at", "created_at")


@admin.register(ReferralProfile)
class ReferralProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "referred_by", "qualified", "created_at")
    list_filter = ("qualified", "created_at")
    search_fields = ("user__username", "user__email", "code")
    readonly_fields = ("code", "created_at")
    raw_id_fields = ("user", "referred_by")


@admin.register(ReferralReward)
class ReferralRewardAdmin(admin.ModelAdmin):
    list_display = ("referrer", "tier", "amount", "created_at")
    list_filter = ("tier", "created_at")
    search_fields = ("referrer__username", "referrer__email")
    readonly_fields = ("referrer", "tier", "amount", "created_at")

    def has_add_permission(self, request):
        return False
