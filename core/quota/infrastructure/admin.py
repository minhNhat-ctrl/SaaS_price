from django.contrib import admin
from core.quota.infrastructure.django_models import UsageRecordModel, UsageEventModel


@admin.register(UsageRecordModel)
class UsageRecordAdmin(admin.ModelAdmin):
    """Admin interface for viewing usage records (read-only audit)."""

    list_display = ("id", "tenant_id", "metric_code", "current_usage", "period_end", "created_at")
    list_filter = ("metric_code", "period_end", "created_at")
    search_fields = ("tenant_id", "metric_code")
    readonly_fields = ("id", "tenant_id", "metric_code", "current_usage", "period_start", "period_end", "created_at", "updated_at")
    ordering = ("-period_end", "-created_at")

    def has_add_permission(self, request):
        """Disable manual creation of usage records."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Disable deletion of usage records (audit trail)."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing of usage records."""
        return False


@admin.register(UsageEventModel)
class UsageEventAdmin(admin.ModelAdmin):
    """Admin interface for viewing usage event audit trail (read-only)."""

    list_display = ("id", "tenant_id", "metric_code", "amount", "created_at")
    list_filter = ("metric_code", "created_at")
    search_fields = ("tenant_id", "metric_code")
    readonly_fields = ("id", "tenant_id", "metric_code", "amount", "metadata", "created_at")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        """Disable manual creation of events."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Disable deletion of events (immutable audit trail)."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing of events."""
        return False
