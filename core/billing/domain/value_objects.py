from enum import Enum


class BillingContractStatus(str, Enum):
    """Contract lifecycle states."""
    PENDING = "pending"        # Awaiting activation
    ACTIVE = "active"          # Currently active
    PAST_DUE = "past_due"      # Payment overdue
    EXPIRED = "expired"        # Contract period ended
    CANCELED = "canceled"      # Cancelled by user or admin


class PaymentStatus(str, Enum):
    """Payment transaction states."""
    PENDING = "pending"        # Awaiting gateway response
    PROCESSING = "processing"  # Gateway processing
    SUCCESS = "success"        # Payment confirmed
    FAILED = "failed"          # Payment declined
    REFUNDED = "refunded"      # Refund issued


class PaymentGateway(str, Enum):
    """Supported payment gateways."""
    STRIPE = "stripe"
    PAYOS = "payos"
    VNPAY = "vnpay"
    PAYPAL = "paypal"


class BillingEventType(str, Enum):
    """Normalized billing event types from webhooks."""
    # Subscription lifecycle
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_DELETED = "subscription.deleted"
    
    # Payment events
    PAYMENT_INTENT_SUCCEEDED = "payment_intent.succeeded"
    PAYMENT_INTENT_PAYMENT_FAILED = "payment_intent.payment_failed"
    PAYMENT_INTENT_CANCELED = "payment_intent.canceled"
    
    # Charge events
    CHARGE_SUCCEEDED = "charge.succeeded"
    CHARGE_FAILED = "charge.failed"
    CHARGE_REFUNDED = "charge.refunded"
    
    # Invoice events
    INVOICE_PAID = "invoice.paid"
    INVOICE_PAYMENT_FAILED = "invoice.payment_failed"
    INVOICE_PAYMENT_ACTION_REQUIRED = "invoice.payment_action_required"


class BillingCycle:
    """Value object for billing period."""
    
    def __init__(self, start_date, end_date):
        if end_date <= start_date:
            raise ValueError("End date must be after start date")
        self.start_date = start_date
        self.end_date = end_date
    
    def __eq__(self, other):
        if not isinstance(other, BillingCycle):
            return False
        return self.start_date == other.start_date and self.end_date == other.end_date
    
    def __repr__(self):
        return f"BillingCycle({self.start_date.date()} → {self.end_date.date()})"


class Money:
    """Value object for monetary amounts with currency."""
    
    def __init__(self, amount: float, currency: str = "USD"):
        if amount < 0:
            raise ValueError("Amount cannot be negative")
        self.amount = round(amount, 2)
        self.currency = currency.upper()
    
    def __add__(self, other):
        if isinstance(other, Money):
            if self.currency != other.currency:
                raise ValueError(f"Cannot add {self.currency} and {other.currency}")
            return Money(self.amount + other.amount, self.currency)
        return Money(self.amount + other, self.currency)
    
    def __mul__(self, factor):
        return Money(self.amount * factor, self.currency)
    
    def __eq__(self, other):
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency
    
    def __repr__(self):
        return f"{self.currency} {self.amount:.2f}"


class InvoiceLineItem:
    """Value object for invoice line item."""
    
    def __init__(self, description: str, quantity: int, unit_price: Money, tax_rate: float = 0.0):
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if tax_rate < 0 or tax_rate > 1:
            raise ValueError("Tax rate must be between 0 and 1")
        
        self.description = description
        self.quantity = quantity
        self.unit_price = unit_price
        self.tax_rate = tax_rate
    
    @property
    def subtotal(self) -> Money:
        """Calculate subtotal before tax."""
        return self.unit_price * self.quantity
    
    @property
    def tax_amount(self) -> Money:
        """Calculate tax amount."""
        return self.subtotal * self.tax_rate
    
    @property
    def total(self) -> Money:
        """Calculate total including tax."""
        return self.subtotal + self.tax_amount
    
    def __repr__(self):
        return f"InvoiceLineItem({self.description}: {self.quantity} × {self.unit_price})"
