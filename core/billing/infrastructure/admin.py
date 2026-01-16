from django.contrib import admin
from core.billing.infrastructure.django_models import InvoiceModel, InvoiceLineItemModel, PaymentModel


class InvoiceLineItemInline(admin.TabularInline):
    """Inline admin for invoice line items."""
    model = InvoiceLineItemModel
    extra = 0
    readonly_fields = ("id", "description", "quantity", "unit_price_cents", "currency", 
                      "tax_rate", "subtotal_cents", "tax_amount_cents", "total_cents", "created_at")
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(InvoiceModel)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin interface for invoices."""
    
    list_display = ("invoice_number", "tenant_id", "status", "total_display", "issued_at", "due_at", "created_at")
    list_filter = ("status", "issued_at", "due_at", "created_at")
    search_fields = ("invoice_number", "tenant_id")
    readonly_fields = ("id", "tenant_id", "invoice_number", "billing_period_start", "billing_period_end",
                      "subtotal_cents", "tax_total_cents", "total_cents", "currency", "status",
                      "issued_at", "due_at", "paid_at", "created_at", "updated_at")
    ordering = ("-created_at",)
    inlines = [InvoiceLineItemInline]
    
    def total_display(self, obj):
        """Display formatted total."""
        return f"{obj.currency} {obj.total_cents / 100:.2f}"
    total_display.short_description = "Total"
    
    def has_add_permission(self, request):
        """Invoices created via service layer only."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent accidental deletion."""
        return False


@admin.register(PaymentModel)
class PaymentAdmin(admin.ModelAdmin):
    """Admin interface for payments."""
    
    list_display = ("id", "tenant_id", "invoice", "gateway", "status", "amount_display", "created_at", "completed_at")
    list_filter = ("gateway", "status", "created_at", "completed_at")
    search_fields = ("id", "tenant_id", "gateway_transaction_id")
    readonly_fields = ("id", "tenant_id", "invoice", "amount_cents", "currency", "gateway",
                      "status", "gateway_transaction_id", "gateway_response", "created_at", "completed_at")
    ordering = ("-created_at",)
    
    def amount_display(self, obj):
        """Display formatted amount."""
        return f"{obj.currency} {obj.amount_cents / 100:.2f}"
    amount_display.short_description = "Amount"
    
    def has_add_permission(self, request):
        """Payments created via service layer only."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent accidental deletion."""
        return False
