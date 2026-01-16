from __future__ import annotations

from datetime import datetime
from django.db import models
from django.utils import timezone
import uuid


class InvoiceModel(models.Model):
    """Django ORM model for Invoice aggregate."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    invoice_number = models.CharField(max_length=64, unique=True, null=True, blank=True)
    
    # Billing cycle
    billing_period_start = models.DateTimeField()
    billing_period_end = models.DateTimeField()
    
    # Amounts (stored in cents to avoid floating point issues)
    subtotal_cents = models.BigIntegerField(default=0)
    tax_total_cents = models.BigIntegerField(default=0)
    total_cents = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=3, default="USD")
    
    # Status and dates
    status = models.CharField(max_length=20, db_index=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "billing_invoice"
        ordering = ["-created_at"]
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "created_at"]),
            models.Index(fields=["status", "due_at"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.invoice_number or self.id} - {self.status}"


class InvoiceLineItemModel(models.Model):
    """Django ORM model for invoice line items."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        InvoiceModel,
        on_delete=models.CASCADE,
        related_name="line_items"
    )
    
    description = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    unit_price_cents = models.BigIntegerField()
    currency = models.CharField(max_length=3, default="USD")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    
    # Calculated fields (stored for performance)
    subtotal_cents = models.BigIntegerField()
    tax_amount_cents = models.BigIntegerField()
    total_cents = models.BigIntegerField()
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = "billing_invoice_line_item"
        ordering = ["created_at"]
        verbose_name = "Invoice Line Item"
        verbose_name_plural = "Invoice Line Items"
    
    def __str__(self) -> str:
        return f"{self.description} - {self.quantity} × ${self.unit_price_cents / 100:.2f}"


class PaymentModel(models.Model):
    """Django ORM model for Payment aggregate."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    invoice = models.ForeignKey(
        InvoiceModel,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    
    # Payment details
    amount_cents = models.BigIntegerField()
    currency = models.CharField(max_length=3, default="USD")
    gateway = models.CharField(max_length=20)
    status = models.CharField(max_length=20, db_index=True)
    
    # Gateway integration
    gateway_transaction_id = models.CharField(max_length=255, null=True, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "billing_payment"
        ordering = ["-created_at"]
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["invoice", "status"]),
            models.Index(fields=["gateway", "status"]),
            models.Index(fields=["gateway_transaction_id"]),
        ]
    
    def __str__(self) -> str:
        return f"Payment {self.id} - {self.gateway} - {self.status}"
