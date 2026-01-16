from abc import ABC, abstractmethod
from typing import List, Optional
import uuid

from core.billing.domain.entities import Invoice, Payment


class InvoiceRepository(ABC):
    """Repository interface for Invoice aggregate."""
    
    @abstractmethod
    def get_by_id(self, invoice_id: uuid.UUID) -> Optional[Invoice]:
        """Retrieve invoice by ID."""
        pass
    
    @abstractmethod
    def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Retrieve invoice by invoice number."""
        pass
    
    @abstractmethod
    def list_by_tenant(self, tenant_id: uuid.UUID, limit: int = 100) -> List[Invoice]:
        """List invoices for a tenant."""
        pass
    
    @abstractmethod
    def save(self, invoice: Invoice) -> Invoice:
        """Persist invoice."""
        pass
    
    @abstractmethod
    def delete(self, invoice_id: uuid.UUID) -> bool:
        """Delete invoice."""
        pass


class PaymentRepository(ABC):
    """Repository interface for Payment aggregate."""
    
    @abstractmethod
    def get_by_id(self, payment_id: uuid.UUID) -> Optional[Payment]:
        """Retrieve payment by ID."""
        pass
    
    @abstractmethod
    def get_by_invoice(self, invoice_id: uuid.UUID) -> List[Payment]:
        """Retrieve all payments for an invoice."""
        pass
    
    @abstractmethod
    def list_by_tenant(self, tenant_id: uuid.UUID, limit: int = 100) -> List[Payment]:
        """List payments for a tenant."""
        pass
    
    @abstractmethod
    def save(self, payment: Payment) -> Payment:
        """Persist payment."""
        pass
    
    @abstractmethod
    def delete(self, payment_id: uuid.UUID) -> bool:
        """Delete payment."""
        pass
