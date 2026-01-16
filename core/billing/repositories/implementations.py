from typing import List, Optional
import uuid

from core.billing.domain.entities import Invoice, Payment
from core.billing.repositories.interfaces import InvoiceRepository, PaymentRepository


class InMemoryInvoiceRepository(InvoiceRepository):
    """In-memory invoice repository for testing."""
    
    def __init__(self):
        self._invoices = {}
    
    def get_by_id(self, invoice_id: uuid.UUID) -> Optional[Invoice]:
        return self._invoices.get(invoice_id)
    
    def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        for invoice in self._invoices.values():
            if invoice.invoice_number == invoice_number:
                return invoice
        return None
    
    def list_by_tenant(self, tenant_id: uuid.UUID, limit: int = 100) -> List[Invoice]:
        results = [inv for inv in self._invoices.values() if inv.tenant_id == tenant_id]
        return results[:limit]
    
    def save(self, invoice: Invoice) -> Invoice:
        self._invoices[invoice.id] = invoice
        return invoice
    
    def delete(self, invoice_id: uuid.UUID) -> bool:
        if invoice_id in self._invoices:
            del self._invoices[invoice_id]
            return True
        return False


class InMemoryPaymentRepository(PaymentRepository):
    """In-memory payment repository for testing."""
    
    def __init__(self):
        self._payments = {}
    
    def get_by_id(self, payment_id: uuid.UUID) -> Optional[Payment]:
        return self._payments.get(payment_id)
    
    def get_by_invoice(self, invoice_id: uuid.UUID) -> List[Payment]:
        return [p for p in self._payments.values() if p.invoice_id == invoice_id]
    
    def list_by_tenant(self, tenant_id: uuid.UUID, limit: int = 100) -> List[Payment]:
        results = [p for p in self._payments.values() if p.tenant_id == tenant_id]
        return results[:limit]
    
    def save(self, payment: Payment) -> Payment:
        self._payments[payment.id] = payment
        return payment
    
    def delete(self, payment_id: uuid.UUID) -> bool:
        if payment_id in self._payments:
            del self._payments[payment_id]
            return True
        return False
