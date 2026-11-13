from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accountsApp.models import AccountApproval, CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("email", "full_name", "role", "account_status", "is_staff")
    list_filter = ("role", "account_status", "is_staff")
    ordering = ("email",)
    search_fields = ("email", "full_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("full_name",)}),
        (
            "Permissions",
            {"fields": ("role", "account_status", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "password1", "password2", "role", "account_status", "is_staff", "is_superuser"),
            },
        ),
    )


@admin.register(AccountApproval)
class AccountApprovalAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "reviewed_by", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("user__email", "user__full_name")
