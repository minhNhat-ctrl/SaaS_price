"""Django admin registrations for internal user management.

This module wires Django's built-in auth models into the custom
`CustomAdminSite` so internal administrators can manage users,
roles, and permissions from the hash-protected admin portal.
"""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group, Permission

from core.admin_core.infrastructure.custom_admin import default_admin_site

User = get_user_model()


@admin.register(User, site=default_admin_site)
class UserAdmin(DjangoUserAdmin):
    """Admin UI for internal user accounts."""

    # Columns displayed in changelist
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
        "last_login",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)

    # Field organization within the detail form
    fieldsets = (
        ("Authentication", {"fields": ("username", "password")} ),
        (
            "Personal info",
            {"fields": ("first_name", "last_name", "email")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important dates",
            {"fields": ("last_login", "date_joined")},
        ),
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
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )


@admin.register(Group, site=default_admin_site)
class GroupAdmin(admin.ModelAdmin):
    """Admin UI for role/group management."""

    list_display = ("name", "permission_count")
    search_fields = ("name",)
    ordering = ("name",)
    filter_horizontal = ("permissions",)

    @admin.display(description="Permissions")
    def permission_count(self, obj: Group) -> int:
        return obj.permissions.count()


@admin.register(Permission, site=default_admin_site)
class PermissionAdmin(admin.ModelAdmin):
    """Read-only permission catalog for audits."""

    list_display = ("name", "codename", "content_type")
    list_filter = ("content_type",)
    search_fields = ("name", "codename")
    ordering = ("content_type", "codename")
    readonly_fields = ("name", "codename", "content_type")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
