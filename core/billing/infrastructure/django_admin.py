"""
Admin interfaces for Billing module (Contract-Centric).

Read-only interfaces for viewing contracts, payments, events.
BillingProviderConfig is editable (admin-only).
All data creation via service layer.
"""

from django.contrib import admin
from core.admin_core.infrastructure.custom_admin import default_admin_site
from core.billing.infrastructure.django_models import (
    BillingContractModel,
    BillingProviderRefModel,
    BillingPaymentModel,
    BillingEventModel,
    BillingGatewayCustomerModel,
    BillingProviderConfigModel,
)


class BillingProviderRefInline(admin.TabularInline):
    """Inline for provider references."""
    model = BillingProviderRefModel
    extra = 0
    readonly_fields = ("id", "provider", "provider_object_type", "provider_object_id", "is_primary", "created_at")
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(BillingContractModel, site=default_admin_site)
class BillingContractAdmin(admin.ModelAdmin):
    """Admin interface for billing contracts (read-only)."""
    
    list_display = ("id", "account_id", "external_contract_ref", "provider", "status", "started_at", "current_period_end")
    list_filter = ("provider", "status", "started_at")
    search_fields = ("account_id", "external_contract_ref", "provider")
    readonly_fields = ("id", "account_id", "external_contract_ref", "provider", "status", "started_at", "current_period_end", "canceled_at", "metadata", "created_at", "updated_at")
    ordering = ("-created_at",)
    inlines = [BillingProviderRefInline]
    
    def has_add_permission(self, request):
        """Contracts created via service layer only."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Read-only."""
        return False


@admin.register(BillingPaymentModel, site=default_admin_site)
class BillingPaymentAdmin(admin.ModelAdmin):
    """Admin interface for payments (read-only)."""
    
    list_display = ("id", "contract", "provider", "provider_payment_id", "status", "amount_display", "occurred_at")
    list_filter = ("provider", "status", "occurred_at")
    search_fields = ("contract__external_contract_ref", "provider_payment_id", "raw_event_id")
    readonly_fields = ("id", "contract", "provider", "provider_payment_id", "amount_cents", "currency", "status", "raw_event_id", "occurred_at", "created_at", "updated_at")
    ordering = ("-created_at",)
    
    def amount_display(self, obj):
        """Display formatted amount."""
        return f"{obj.currency} {obj.amount_cents / 100:.2f}"
    amount_display.short_description = "Amount"
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(BillingEventModel, site=default_admin_site)
class BillingEventAdmin(admin.ModelAdmin):
    """Admin interface for webhook events (read-only, audit trail)."""
    
    list_display = ("id", "provider", "event_type", "provider_event_id", "contract", "received_at", "processed_at")
    list_filter = ("provider", "event_type", "received_at", "processed_at")
    search_fields = ("provider_event_id", "contract__external_contract_ref")
    readonly_fields = ("id", "provider", "event_type", "provider_event_id", "payload_hash", "contract", "received_at", "processed_at", "created_at")
    ordering = ("-received_at",)
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(BillingGatewayCustomerModel, site=default_admin_site)
class BillingGatewayCustomerAdmin(admin.ModelAdmin):
    """Admin interface for gateway customers (read-only)."""
    
    list_display = ("id", "account_id", "provider", "provider_customer_id", "created_at")
    list_filter = ("provider", "created_at")
    search_fields = ("account_id", "provider_customer_id")
    readonly_fields = ("id", "account_id", "provider", "provider_customer_id", "metadata", "created_at", "updated_at")
    ordering = ("-created_at",)
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(BillingProviderConfigModel, site=default_admin_site)
class BillingProviderConfigAdmin(admin.ModelAdmin):
    """Admin interface for provider configuration (editable by admins only)."""
    
    list_display = ("provider", "environment", "is_active", "created_at")
    list_filter = ("provider", "environment", "is_active")
    search_fields = ("provider", "environment")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        ('Provider', {
            'fields': ('id', 'provider', 'environment', 'is_active')
        }),
        ('Credentials', {
            'fields': ('credentials_json',),
            'classes': ('collapse',),
            'description': 'JSON credentials (encrypted in storage). Example: {"api_key": "sk_...", "secret_key": "..."}'
        }),
        ('Webhook', {
            'fields': ('webhook_secret',),
            'description': 'Webhook signature secret for validating incoming webhooks'
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    ordering = ('provider', 'environment')
    
    def has_delete_permission(self, request, obj=None):
        """Prevent accidental deletion of config."""
        return False
