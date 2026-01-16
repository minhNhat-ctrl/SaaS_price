"""
Django ORM models for Billing module (Contract-Centric).

Models:
- BillingContractModel: Main contract entity
- BillingProviderRefModel: Contract ↔ Gateway mapping
- BillingPaymentModel: Payment records (audit trail)
- BillingEventModel: Webhook events (idempotency)
- BillingGatewayCustomerModel: Account ↔ Gateway customer
- BillingProviderConfigModel: Gateway credentials (encrypted)
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone
import uuid


class BillingContractModel(models.Model):
    """
    BillingContract ORM model.
    
    Central contract entity - opaque to business logic.
    Does NOT contain plan, product, feature, usage, or limit info.
    """
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('expired', 'Expired'),
        ('canceled', 'Canceled'),
    )
    
    GATEWAY_CHOICES = (
        ('stripe', 'Stripe'),
        ('payos', 'PayOS'),
        ('vnpay', 'VNPay'),
        ('paypal', 'PayPal'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Billing info
    account_id = models.UUIDField(db_index=True, help_text="Who is paying")
    external_contract_ref = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Opaque reference to other modules (subscription_id, tenant_id, etc.)"
    )
    
    # Gateway
    provider = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    
    # Status & Dates
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata (opaque JSON)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Audit
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "billing_contract"
        verbose_name = "Billing Contract"
        verbose_name_plural = "Billing Contracts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['account_id', 'status']),
            models.Index(fields=['account_id', '-started_at']),
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['external_contract_ref']),
        ]
    
    def __str__(self) -> str:
        return f"{self.external_contract_ref} ({self.provider}/{self.status})"


class BillingProviderRefModel(models.Model):
    """
    Maps BillingContract ↔ gateway provider objects.
    
    Allows:
    - 1 contract → multiple provider objects
    - Migration from one gateway to another
    - Audit trail of provider changes
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    contract = models.ForeignKey(
        BillingContractModel,
        on_delete=models.CASCADE,
        related_name='provider_refs'
    )
    
    provider = models.CharField(max_length=20)
    provider_object_type = models.CharField(
        max_length=50,
        help_text="subscription, payment_intent, customer, etc."
    )
    provider_object_id = models.CharField(
        max_length=255,
        help_text="Stripe sub_id, PaymentIntent ID, etc."
    )
    
    is_primary = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = "billing_provider_ref"
        verbose_name = "Provider Reference"
        verbose_name_plural = "Provider References"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contract', 'is_primary']),
            models.Index(fields=['provider', 'provider_object_id']),
        ]
        unique_together = [('provider', 'provider_object_id')]
    
    def __str__(self) -> str:
        return f"{self.provider}/{self.provider_object_type}:{self.provider_object_id}"


class BillingPaymentModel(models.Model):
    """
    BillingPayment ORM model - minimal payment record.
    
    Captures: who paid, how much, when, status.
    Does NOT validate eligibility or amounts.
    
    Purpose: audit trail + support data.
    """
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    GATEWAY_CHOICES = (
        ('stripe', 'Stripe'),
        ('payos', 'PayOS'),
        ('vnpay', 'VNPay'),
        ('paypal', 'PayPal'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    contract = models.ForeignKey(
        BillingContractModel,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    provider = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    provider_payment_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Stripe charge ID, PayOS transaction ID, etc."
    )
    
    # Amount (in cents)
    amount_cents = models.BigIntegerField()
    currency = models.CharField(max_length=3, default='USD')
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    # Webhook
    raw_event_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Stripe event ID, webhook event ID, etc."
    )
    
    occurred_at = models.DateTimeField(default=timezone.now)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "billing_payment"
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['contract', 'status']),
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['provider_payment_id']),
            models.Index(fields=['raw_event_id']),
        ]
    
    def __str__(self) -> str:
        return f"{self.provider}/{self.provider_payment_id} - {self.status}"


class BillingEventModel(models.Model):
    """
    BillingEvent ORM model - normalized webhook events.
    
    Provides:
    - Idempotency via payload_hash (prevents duplicate processing)
    - Debug trail (received vs processed status)
    - Replay capability (reprocess events if needed)
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Source
    provider = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Payment gateway provider (stripe, payos, vnpay, paypal, custom-provider, etc.)"
    )
    event_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="subscription.created, charge.succeeded, etc."
    )
    provider_event_id = models.CharField(
        max_length=255,
        db_index=True,
        unique=True,
        help_text="Unique event ID from gateway (for idempotency)"
    )
    
    # Payload
    payload_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA256 hash of payload (for duplicate detection)"
    )
    
    # Association
    contract = models.ForeignKey(
        BillingContractModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events'
    )
    
    # Status
    received_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = "billing_event"
        verbose_name = "Billing Event"
        verbose_name_plural = "Billing Events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['provider', 'event_type']),
            models.Index(fields=['provider_event_id']),
            models.Index(fields=['processed_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.provider}/{self.event_type} @ {self.received_at}"


class BillingGatewayCustomerModel(models.Model):
    """
    Maps account_id ↔ gateway customer.
    
    Allows:
    - Store customer metadata per provider
    - Track customer creation date
    - Support multi-provider accounts
    """
    
    GATEWAY_CHOICES = (
        ('stripe', 'Stripe'),
        ('payos', 'PayOS'),
        ('vnpay', 'VNPay'),
        ('paypal', 'PayPal'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    account_id = models.UUIDField(db_index=True)
    provider = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    provider_customer_id = models.CharField(max_length=255, db_index=True)
    
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "billing_gateway_customer"
        verbose_name = "Gateway Customer"
        verbose_name_plural = "Gateway Customers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['account_id', 'provider']),
            models.Index(fields=['provider_customer_id']),
        ]
        unique_together = [('account_id', 'provider')]
    
    def __str__(self) -> str:
        return f"{self.account_id} @ {self.provider}"


class BillingProviderConfigModel(models.Model):
    """
    BillingProviderConfig - gateway credentials & configuration.
    
    Admin-only model (no API access).
    Credentials stored encrypted (via settings).
    """
    
    ENVIRONMENT_CHOICES = (
        ('sandbox', 'Sandbox'),
        ('production', 'Production'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    provider = models.CharField(
        max_length=100, 
        db_index=True,
        help_text="Payment gateway provider (stripe, payos, vnpay, paypal, momo, zalopay, custom-provider, etc.)"
    )
    environment = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES)
    
    # Credentials (encrypted via Django settings middleware)
    credentials_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Encrypted JSON containing API keys, etc. Example: {\"api_key\": \"sk_...\", \"secret_key\": ...}"
    )
    webhook_secret = models.CharField(
        max_length=255,
        blank=True,
        help_text="Webhook signature secret"
    )
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "billing_provider_config"
        verbose_name = "Provider Configuration"
        verbose_name_plural = "Provider Configurations"
        unique_together = [('provider', 'environment')]
    
    def __str__(self) -> str:
        return f"{self.provider} ({self.environment})"


# ============================================================================
# DEPRECATED MODELS (kept for migration compatibility)
# These will be removed in future versions once data is migrated
# ============================================================================

class InvoiceModel(models.Model):
    """DEPRECATED - Use BillingContractModel instead."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    invoice_number = models.CharField(max_length=64, unique=True, null=True, blank=True)
    
    billing_period_start = models.DateTimeField()
    billing_period_end = models.DateTimeField()
    
    subtotal_cents = models.BigIntegerField(default=0)
    tax_total_cents = models.BigIntegerField(default=0)
    total_cents = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=3, default="USD")
    
    status = models.CharField(max_length=20, db_index=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "billing_invoice"
        ordering = ["-created_at"]
        verbose_name = "Invoice (DEPRECATED)"
        verbose_name_plural = "Invoices (DEPRECATED)"


class InvoiceLineItemModel(models.Model):
    """DEPRECATED - Use BillingContractModel instead."""
    
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
    
    subtotal_cents = models.BigIntegerField()
    tax_amount_cents = models.BigIntegerField()
    total_cents = models.BigIntegerField()
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = "billing_invoice_line_item"
        ordering = ["created_at"]
        verbose_name = "Invoice Line Item (DEPRECATED)"
        verbose_name_plural = "Invoice Line Items (DEPRECATED)"
