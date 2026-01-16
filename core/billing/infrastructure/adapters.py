from typing import List, Optional
import uuid

from core.billing.domain.entities import Invoice, Payment
from core.billing.domain.value_objects import (
    InvoiceStatus,
    PaymentStatus,
    PaymentGateway,
    Money,
    InvoiceLineItem,
    BillingCycle,
)
from core.billing.repositories.interfaces import InvoiceRepository, PaymentRepository
from core.billing.infrastructure.django_models import InvoiceModel, InvoiceLineItemModel, PaymentModel


class DjangoORMInvoiceRepository(InvoiceRepository):
    """Django ORM implementation of InvoiceRepository."""
    
    @staticmethod
    def _model_to_entity(model: InvoiceModel) -> Invoice:
        """Convert ORM model to domain entity."""
        # Reconstruct line items
        line_items = []
        for item_model in model.line_items.all():
            line_item = InvoiceLineItem(
                description=item_model.description,
                quantity=item_model.quantity,
                unit_price=Money(item_model.unit_price_cents / 100, item_model.currency),
                tax_rate=float(item_model.tax_rate),
            )
            line_items.append(line_item)
        
        return Invoice(
            id=model.id,
            tenant_id=model.tenant_id,
            invoice_number=model.invoice_number,
            billing_cycle=BillingCycle(model.billing_period_start, model.billing_period_end),
            line_items=line_items,
            status=InvoiceStatus(model.status),
            issued_at=model.issued_at,
            due_at=model.due_at,
            paid_at=model.paid_at,
        )
    
    @staticmethod
    def _entity_to_model(entity: Invoice) -> InvoiceModel:
        """Convert domain entity to ORM model."""
        model = InvoiceModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            invoice_number=entity.invoice_number,
            billing_period_start=entity.billing_cycle.start_date,
            billing_period_end=entity.billing_cycle.end_date,
            subtotal_cents=int(entity.subtotal.amount * 100),
            tax_total_cents=int(entity.tax_total.amount * 100),
            total_cents=int(entity.total.amount * 100),
            currency=entity.total.currency,
            status=entity.status.value,
            issued_at=entity.issued_at,
            due_at=entity.due_at,
            paid_at=entity.paid_at,
        )
        return model
    
    def get_by_id(self, invoice_id: uuid.UUID) -> Optional[Invoice]:
        try:
            model = InvoiceModel.objects.prefetch_related('line_items').get(id=invoice_id)
            return self._model_to_entity(model)
        except InvoiceModel.DoesNotExist:
            return None
    
    def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        try:
            model = InvoiceModel.objects.prefetch_related('line_items').get(invoice_number=invoice_number)
            return self._model_to_entity(model)
        except InvoiceModel.DoesNotExist:
            return None
    
    def list_by_tenant(self, tenant_id: uuid.UUID, limit: int = 100) -> List[Invoice]:
        models = InvoiceModel.objects.filter(tenant_id=tenant_id).prefetch_related('line_items')[:limit]
        return [self._model_to_entity(m) for m in models]
    
    def save(self, entity: Invoice) -> Invoice:
        """Save invoice and line items."""
        model = self._entity_to_model(entity)
        model.save()
        
        # Delete existing line items
        InvoiceLineItemModel.objects.filter(invoice=model).delete()
        
        # Create new line items
        for item in entity.line_items:
            InvoiceLineItemModel.objects.create(
                invoice=model,
                description=item.description,
                quantity=item.quantity,
                unit_price_cents=int(item.unit_price.amount * 100),
                currency=item.unit_price.currency,
                tax_rate=item.tax_rate,
                subtotal_cents=int(item.subtotal.amount * 100),
                tax_amount_cents=int(item.tax_amount.amount * 100),
                total_cents=int(item.total.amount * 100),
            )
        
        return self._model_to_entity(model)
    
    def delete(self, invoice_id: uuid.UUID) -> bool:
        try:
            InvoiceModel.objects.get(id=invoice_id).delete()
            return True
        except InvoiceModel.DoesNotExist:
            return False


class DjangoORMPaymentRepository(PaymentRepository):
    """Django ORM implementation of PaymentRepository."""
    
    @staticmethod
    def _model_to_entity(model: PaymentModel) -> Payment:
        """Convert ORM model to domain entity."""
        return Payment(
            id=model.id,
            tenant_id=model.tenant_id,
            invoice_id=model.invoice_id,
            amount=Money(model.amount_cents / 100, model.currency),
            gateway=PaymentGateway(model.gateway),
            status=PaymentStatus(model.status),
            gateway_transaction_id=model.gateway_transaction_id,
            gateway_response=model.gateway_response,
            created_at=model.created_at,
            completed_at=model.completed_at,
        )
    
    @staticmethod
    def _entity_to_model(entity: Payment) -> PaymentModel:
        """Convert domain entity to ORM model."""
        return PaymentModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            invoice_id=entity.invoice_id,
            amount_cents=int(entity.amount.amount * 100),
            currency=entity.amount.currency,
            gateway=entity.gateway.value,
            status=entity.status.value,
            gateway_transaction_id=entity.gateway_transaction_id,
            gateway_response=entity.gateway_response,
            created_at=entity.created_at,
            completed_at=entity.completed_at,
        )
    
    def get_by_id(self, payment_id: uuid.UUID) -> Optional[Payment]:
        try:
            model = PaymentModel.objects.get(id=payment_id)
            return self._model_to_entity(model)
        except PaymentModel.DoesNotExist:
            return None
    
    def get_by_invoice(self, invoice_id: uuid.UUID) -> List[Payment]:
        models = PaymentModel.objects.filter(invoice_id=invoice_id)
        return [self._model_to_entity(m) for m in models]
    
    def list_by_tenant(self, tenant_id: uuid.UUID, limit: int = 100) -> List[Payment]:
        models = PaymentModel.objects.filter(tenant_id=tenant_id)[:limit]
        return [self._model_to_entity(m) for m in models]
    
    def save(self, entity: Payment) -> Payment:
        model = self._entity_to_model(entity)
        model.save()
        return self._model_to_entity(model)
    
    def delete(self, payment_id: uuid.UUID) -> bool:
        try:
            PaymentModel.objects.get(id=payment_id).delete()
            return True
        except PaymentModel.DoesNotExist:
            return False
