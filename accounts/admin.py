from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserSettings


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User

    list_display = (
        "username",
        "email",
        "created_at",
        "last_login",
    )

    search_fields = (
        "username",
        "email",
    )

    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "created_at",
        "last_login",
    )

    fieldsets = (
        ("Account Information", {
            "fields": (
                "username",
                "email",
                "password",
            )
        }),
        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Important Dates", {
            "fields": (
                "created_at",
                "last_login",
            )
        }),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "email_notifications",
        "order_notifications",
    )

    search_fields = (
        "user__username",
        "user__email",
    )