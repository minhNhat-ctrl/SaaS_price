from datetime import datetime, timedelta
from typing import List, Dict
import uuid

from core.billing.domain.entities import Invoice, Payment
from core.billing.domain.value_objects import (
    InvoiceStatus,
    PaymentStatus,
    Money,
    InvoiceLineItem,
    BillingCycle,
    PaymentGateway,
)
from core.billing.domain.exceptions import InvoiceNotFoundError, PaymentGatewayError
from core.billing.repositories.interfaces import InvoiceRepository, PaymentRepository
from core.billing.services.payment_gateway import PaymentGatewayInterface, PaymentGatewayFactory


class InvoiceService:
    """Service for invoice generation and management."""
    
    def __init__(self, invoice_repo: InvoiceRepository):
        self.invoice_repo = invoice_repo
    
    def generate_invoice_number(self) -> str:
        """Generate unique invoice number."""
        timestamp = datetime.now().strftime("%Y%m%d")
        random_suffix = uuid.uuid4().hex[:8].upper()
        return f"INV-{timestamp}-{random_suffix}"
    
    def create_invoice(
        self,
        tenant_id: uuid.UUID,
        billing_cycle: BillingCycle,
        line_items: List[InvoiceLineItem],
    ) -> Invoice:
        """Create draft invoice."""
        invoice = Invoice(
            tenant_id=tenant_id,
            billing_cycle=billing_cycle,
            line_items=line_items,
            status=InvoiceStatus.DRAFT,
        )
        return self.invoice_repo.save(invoice)
    
    def issue_invoice(
        self,
        invoice_id: uuid.UUID,
        due_days: int = 30,
    ) -> Invoice:
        """Issue invoice (draft → pending)."""
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise InvoiceNotFoundError(invoice_id)
        
        invoice_number = self.generate_invoice_number()
        issued_at = datetime.now()
        due_at = issued_at + timedelta(days=due_days)
        
        invoice.issue(invoice_number, issued_at, due_at)
        return self.invoice_repo.save(invoice)
    
    def mark_invoice_paid(
        self,
        invoice_id: uuid.UUID,
        paid_at: datetime = None,
    ) -> Invoice:
        """Mark invoice as paid."""
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise InvoiceNotFoundError(invoice_id)
        
        invoice.mark_paid(paid_at or datetime.now())
        return self.invoice_repo.save(invoice)
    
    def mark_overdue_invoices(self) -> int:
        """Mark pending invoices past due date as overdue."""
        # TODO: Implement batch update
        # This would typically be run as a scheduled task
        return 0
    
    def calculate_invoice_from_usage(
        self,
        tenant_id: uuid.UUID,
        billing_cycle: BillingCycle,
        usage_data: Dict,
    ) -> Invoice:
        """
        Calculate invoice from usage data (integration with quota module).
        
        Args:
            tenant_id: Tenant UUID
            billing_cycle: Billing period
            usage_data: Dict with usage metrics (e.g., {'tracked_products': 45})
        
        Returns:
            Draft invoice
        """
        # This is a placeholder - full integration would query:
        # 1. Subscription module for active plan
        # 2. Pricing module for plan details
        # 3. Quota module for actual usage
        # 4. Calculate overage charges
        
        line_items = []
        
        # Example: Base subscription fee
        line_items.append(
            InvoiceLineItem(
                description="Monthly Subscription",
                quantity=1,
                unit_price=Money(149.00, "USD"),
                tax_rate=0.0,
            )
        )
        
        # Example: Usage overage
        if usage_data.get("tracked_products", 0) > 500:
            overage = usage_data["tracked_products"] - 500
            line_items.append(
                InvoiceLineItem(
                    description=f"Additional Products ({overage} units)",
                    quantity=overage,
                    unit_price=Money(0.50, "USD"),
                    tax_rate=0.0,
                )
            )
        
        return self.create_invoice(tenant_id, billing_cycle, line_items)


class PaymentService:
    """Service for payment processing."""
    
    def __init__(
        self,
        payment_repo: PaymentRepository,
        invoice_repo: InvoiceRepository,
    ):
        self.payment_repo = payment_repo
        self.invoice_repo = invoice_repo
    
    def initiate_payment(
        self,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        gateway: PaymentGateway,
        gateway_config: Dict,
    ) -> Dict:
        """
        Initiate payment for invoice.
        
        Returns:
            Dict with payment details and redirect URL
        """
        # Get invoice
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise InvoiceNotFoundError(invoice_id)
        
        # Create payment record
        payment = Payment(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            amount=invoice.total,
            gateway=gateway,
            status=PaymentStatus.PENDING,
        )
        payment = self.payment_repo.save(payment)
        
        # Create payment intent with gateway
        try:
            gateway_client = PaymentGatewayFactory.create(gateway, gateway_config)
            result = gateway_client.create_payment_intent(
                amount=invoice.total,
                metadata={
                    "invoice_id": str(invoice_id),
                    "tenant_id": str(tenant_id),
                }
            )
            
            # Update payment with gateway transaction ID
            payment.mark_processing(result["transaction_id"])
            payment = self.payment_repo.save(payment)
            
            return {
                "payment_id": str(payment.id),
                "transaction_id": result["transaction_id"],
                "redirect_url": result["redirect_url"],
                "amount": invoice.total.amount,
                "currency": invoice.total.currency,
            }
        
        except Exception as e:
            payment.mark_failed({"error": str(e)})
            self.payment_repo.save(payment)
            raise PaymentGatewayError(gateway.value, str(e))
    
    def verify_payment(
        self,
        payment_id: uuid.UUID,
        gateway_config: Dict,
    ) -> Payment:
        """Verify payment status with gateway."""
        payment = self.payment_repo.get_by_id(payment_id)
        if not payment:
            raise PaymentGatewayError("unknown", f"Payment not found: {payment_id}")
        
        try:
            gateway_client = PaymentGatewayFactory.create(payment.gateway, gateway_config)
            result = gateway_client.verify_payment(payment.gateway_transaction_id)
            
            if result["status"] == "success":
                payment.mark_success(
                    completed_at=result.get("completed_at") or datetime.now(),
                    gateway_response=result
                )
                payment = self.payment_repo.save(payment)
                
                # Mark invoice as paid
                invoice = self.invoice_repo.get_by_id(payment.invoice_id)
                if invoice:
                    invoice.mark_paid(payment.completed_at)
                    self.invoice_repo.save(invoice)
            
            elif result["status"] == "failed":
                payment.mark_failed(result)
                payment = self.payment_repo.save(payment)
            
            return payment
        
        except Exception as e:
            raise PaymentGatewayError(payment.gateway.value, str(e))
    
    def refund_payment(
        self,
        payment_id: uuid.UUID,
        gateway_config: Dict,
        amount: Money = None,
    ) -> Payment:
        """Refund payment."""
        payment = self.payment_repo.get_by_id(payment_id)
        if not payment:
            raise PaymentGatewayError("unknown", f"Payment not found: {payment_id}")
        
        try:
            gateway_client = PaymentGatewayFactory.create(payment.gateway, gateway_config)
            result = gateway_client.refund_payment(payment.gateway_transaction_id, amount)
            
            if result["status"] == "success":
                payment.refund()
                payment = self.payment_repo.save(payment)
                
                # Mark invoice as refunded
                invoice = self.invoice_repo.get_by_id(payment.invoice_id)
                if invoice:
                    invoice.refund()
                    self.invoice_repo.save(invoice)
            
            return payment
        
        except Exception as e:
            raise PaymentGatewayError(payment.gateway.value, str(e))
