from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import uuid

from core.billing.domain.value_objects import (
    InvoiceStatus,
    PaymentStatus,
    PaymentGateway,
    Money,
    InvoiceLineItem,
    BillingCycle,
)
from core.billing.domain.exceptions import InvalidInvoiceStateError


class Invoice:
    """Invoice aggregate root."""
    
    def __init__(
        self,
        tenant_id: uuid.UUID,
        billing_cycle: BillingCycle,
        line_items: List[InvoiceLineItem],
        id: Optional[uuid.UUID] = None,
        invoice_number: Optional[str] = None,
        status: InvoiceStatus = InvoiceStatus.DRAFT,
        issued_at: Optional[datetime] = None,
        due_at: Optional[datetime] = None,
        paid_at: Optional[datetime] = None,
    ):
        self.id = id or uuid.uuid4()
        self.tenant_id = tenant_id
        self.invoice_number = invoice_number
        self.billing_cycle = billing_cycle
        self.line_items = line_items
        self.status = status
        self.issued_at = issued_at
        self.due_at = due_at
        self.paid_at = paid_at
    
    @property
    def subtotal(self) -> Money:
        """Calculate total before tax."""
        if not self.line_items:
            return Money(0)
        total = self.line_items[0].subtotal
        for item in self.line_items[1:]:
            total = total + item.subtotal
        return total
    
    @property
    def tax_total(self) -> Money:
        """Calculate total tax amount."""
        if not self.line_items:
            return Money(0)
        total = self.line_items[0].tax_amount
        for item in self.line_items[1:]:
            total = total + item.tax_amount
        return total
    
    @property
    def total(self) -> Money:
        """Calculate grand total."""
        return self.subtotal + self.tax_total
    
    def issue(self, invoice_number: str, issued_at: datetime, due_at: datetime) -> None:
        """Issue the invoice (draft → pending)."""
        if self.status != InvoiceStatus.DRAFT:
            raise InvalidInvoiceStateError(self.status, "issue")
        
        self.invoice_number = invoice_number
        self.issued_at = issued_at
        self.due_at = due_at
        self.status = InvoiceStatus.PENDING
    
    def mark_paid(self, paid_at: datetime) -> None:
        """Mark invoice as paid."""
        if self.status not in [InvoiceStatus.PENDING, InvoiceStatus.OVERDUE]:
            raise InvalidInvoiceStateError(self.status, "mark_paid")
        
        self.paid_at = paid_at
        self.status = InvoiceStatus.PAID
    
    def mark_overdue(self) -> None:
        """Mark invoice as overdue."""
        if self.status != InvoiceStatus.PENDING:
            raise InvalidInvoiceStateError(self.status, "mark_overdue")
        
        self.status = InvoiceStatus.OVERDUE
    
    def cancel(self) -> None:
        """Cancel invoice."""
        if self.status in [InvoiceStatus.PAID, InvoiceStatus.REFUNDED]:
            raise InvalidInvoiceStateError(self.status, "cancel")
        
        self.status = InvoiceStatus.CANCELLED
    
    def refund(self) -> None:
        """Refund paid invoice."""
        if self.status != InvoiceStatus.PAID:
            raise InvalidInvoiceStateError(self.status, "refund")
        
        self.status = InvoiceStatus.REFUNDED
    
    def __repr__(self):
        return f"Invoice({self.invoice_number or self.id}, {self.status}, {self.total})"


class Payment:
    """Payment aggregate root."""
    
    def __init__(
        self,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        amount: Money,
        gateway: PaymentGateway,
        id: Optional[uuid.UUID] = None,
        status: PaymentStatus = PaymentStatus.PENDING,
        gateway_transaction_id: Optional[str] = None,
        gateway_response: Optional[dict] = None,
        created_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ):
        self.id = id or uuid.uuid4()
        self.tenant_id = tenant_id
        self.invoice_id = invoice_id
        self.amount = amount
        self.gateway = gateway
        self.status = status
        self.gateway_transaction_id = gateway_transaction_id
        self.gateway_response = gateway_response or {}
        self.created_at = created_at or datetime.now()
        self.completed_at = completed_at
    
    def mark_processing(self, gateway_transaction_id: str) -> None:
        """Mark payment as processing."""
        if self.status != PaymentStatus.PENDING:
            raise InvalidInvoiceStateError(self.status, "mark_processing")
        
        self.gateway_transaction_id = gateway_transaction_id
        self.status = PaymentStatus.PROCESSING
    
    def mark_success(self, completed_at: datetime, gateway_response: dict = None) -> None:
        """Mark payment as successful."""
        if self.status not in [PaymentStatus.PENDING, PaymentStatus.PROCESSING]:
            raise InvalidInvoiceStateError(self.status, "mark_success")
        
        self.completed_at = completed_at
        self.status = PaymentStatus.SUCCESS
        if gateway_response:
            self.gateway_response = gateway_response
    
    def mark_failed(self, gateway_response: dict = None) -> None:
        """Mark payment as failed."""
        if self.status not in [PaymentStatus.PENDING, PaymentStatus.PROCESSING]:
            raise InvalidInvoiceStateError(self.status, "mark_failed")
        
        self.status = PaymentStatus.FAILED
        if gateway_response:
            self.gateway_response = gateway_response
    
    def cancel(self) -> None:
        """Cancel payment."""
        if self.status in [PaymentStatus.SUCCESS, PaymentStatus.REFUNDED]:
            raise InvalidInvoiceStateError(self.status, "cancel")
        
        self.status = PaymentStatus.CANCELLED
    
    def refund(self) -> None:
        """Refund payment."""
        if self.status != PaymentStatus.SUCCESS:
            raise InvalidInvoiceStateError(self.status, "refund")
        
        self.status = PaymentStatus.REFUNDED
    
    def __repr__(self):
        return f"Payment({self.id}, {self.gateway}, {self.status}, {self.amount})"
