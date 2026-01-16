# Billing Module - Invoice & Payment Processing

**Status**: ✅ Infrastructure Complete (Temporary - No Runtime Flow)  
**Date**: 2026-01-15

## Overview

The Billing module handles invoice generation and payment processing for the SaaS platform. It integrates with pricing, subscription, and quota modules to calculate charges and process payments through multiple gateways.

## Responsibilities

1. **Calculate Charges** — Generate invoices from usage/subscription data
2. **Issue Invoices** — Create and manage invoice lifecycle
3. **Process Payments** — Handle payments via multiple gateways (Stripe, PayOS, VNPay)
4. **Track Status** — Monitor invoice and payment states

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                  Billing Module Flow                       │
└────────────────────────────────────────────────────────────┘

Usage/Subscription Data
         ↓
   InvoiceService
   (Calculate charges)
         ↓
      Invoice
   (Draft → Pending)
         ↓
   PaymentService
   (Initiate payment)
         ↓
  PaymentGateway
  (Stripe/PayOS/VNPay)
         ↓
     Payment
  (Pending → Success)
         ↓
    Invoice Paid
```

## Domain Model

### Entities

#### Invoice Aggregate
```python
Invoice(
    tenant_id,
    billing_cycle: BillingCycle,
    line_items: List[InvoiceLineItem],
    status: InvoiceStatus,
    invoice_number,
    issued_at,
    due_at,
    paid_at
)
```

**States**:
- `DRAFT` — Being prepared
- `PENDING` — Awaiting payment
- `PAID` — Payment confirmed
- `OVERDUE` — Past due date
- `CANCELLED` — Voided
- `REFUNDED` — Refund issued

**Methods**:
- `issue()` — Draft → Pending
- `mark_paid()` — Mark as paid
- `mark_overdue()` — Mark overdue
- `cancel()` — Cancel invoice
- `refund()` — Issue refund

#### Payment Aggregate
```python
Payment(
    tenant_id,
    invoice_id,
    amount: Money,
    gateway: PaymentGateway,
    status: PaymentStatus,
    gateway_transaction_id,
    gateway_response
)
```

**States**:
- `PENDING` — Awaiting gateway
- `PROCESSING` — Gateway processing
- `SUCCESS` — Confirmed
- `FAILED` — Declined
- `CANCELLED` — User cancelled
- `REFUNDED` — Refund issued

### Value Objects

#### Money
```python
Money(amount: float, currency: str = "USD")
# Operations: +, *, ==
# Example: Money(149.00, "USD")
```

#### InvoiceLineItem
```python
InvoiceLineItem(
    description: str,
    quantity: int,
    unit_price: Money,
    tax_rate: float = 0.0
)

# Calculated properties:
# .subtotal → quantity × unit_price
# .tax_amount → subtotal × tax_rate
# .total → subtotal + tax
```

#### BillingCycle
```python
BillingCycle(start_date, end_date)
# Validates: end_date > start_date
```

## Infrastructure

### ORM Models

**InvoiceModel**:
- `billing_invoice` table
- Fields: id (UUID), tenant_id, invoice_number (unique), billing_period_start/end, amounts in cents, status, dates
- Indexes:
  - (tenant_id, status)
  - (tenant_id, created_at)
  - (status, due_at)

**InvoiceLineItemModel**:
- `billing_invoice_line_item` table
- ForeignKey → InvoiceModel
- Fields: description, quantity, unit_price_cents, tax_rate, calculated amounts

**PaymentModel**:
- `billing_payment` table
- ForeignKey → InvoiceModel
- Fields: id (UUID), tenant_id, invoice_id, amount_cents, gateway, status, gateway_transaction_id, gateway_response (JSON)
- Indexes:
  - (tenant_id, status)
  - (invoice_id, status)
  - (gateway, status)
  - (gateway_transaction_id)

### Why Amounts in Cents?
Stored as `BigIntegerField` (cents) to avoid floating point precision issues:
```python
$149.99 → 14999 cents
```

## Services Layer

### InvoiceService

**Purpose**: Generate and manage invoices

**Methods**:
```python
create_invoice(tenant_id, billing_cycle, line_items) → Invoice
  # Create draft invoice

issue_invoice(invoice_id, due_days=30) → Invoice
  # Issue invoice (draft → pending)

mark_invoice_paid(invoice_id, paid_at) → Invoice
  # Mark as paid

calculate_invoice_from_usage(tenant_id, billing_cycle, usage_data) → Invoice
  # Generate invoice from usage (integrates with pricing/quota modules)
```

**Example Usage**:
```python
service = InvoiceService(invoice_repo)

# Create invoice
line_items = [
    InvoiceLineItem("Monthly Subscription", 1, Money(149, "USD")),
    InvoiceLineItem("Overage (50 units)", 50, Money(0.50, "USD"))
]
invoice = service.create_invoice(tenant_id, billing_cycle, line_items)

# Issue invoice
invoice = service.issue_invoice(invoice.id, due_days=14)
```

### PaymentService

**Purpose**: Process payments via gateways

**Methods**:
```python
initiate_payment(tenant_id, invoice_id, gateway, gateway_config) → Dict
  # Create payment intent, returns redirect URL

verify_payment(payment_id, gateway_config) → Payment
  # Verify payment status, updates invoice if successful

refund_payment(payment_id, gateway_config, amount=None) → Payment
  # Issue refund
```

**Example Usage**:
```python
service = PaymentService(payment_repo, invoice_repo)

# Initiate payment
result = service.initiate_payment(
    tenant_id=...,
    invoice_id=...,
    gateway=PaymentGateway.STRIPE,
    gateway_config={"api_key": "sk_test_..."}
)
# Returns: {"payment_id", "transaction_id", "redirect_url", "amount", "currency"}

# User completes payment via redirect_url

# Verify payment
payment = service.verify_payment(result["payment_id"], gateway_config)
# If successful: invoice marked as paid, payment status = SUCCESS
```

## Payment Gateway Abstraction

### PaymentGatewayInterface
```python
class PaymentGatewayInterface(ABC):
    def create_payment_intent(amount, metadata) → Dict
    def verify_payment(transaction_id) → Dict
    def refund_payment(transaction_id, amount) → Dict
```

### Supported Gateways

**Stripe** (`StripeGateway`)
- **Status**: Placeholder (not implemented)
- **Config**: `{"api_key": "sk_test_..."}`

**PayOS** (`PayOSGateway`)
- **Status**: Placeholder (not implemented)
- **Config**: `{"api_key": "...", "client_id": "..."}`

**VNPay** (`VNPayGateway`)
- **Status**: Placeholder (not implemented)
- **Config**: `{"terminal_id": "...", "secret_key": "..."}`

**Manual** (`PaymentGateway.MANUAL`)
- For offline/bank transfer payments

### Gateway Factory
```python
gateway = PaymentGatewayFactory.create(
    gateway=PaymentGateway.STRIPE,
    config={"api_key": "sk_test_..."}
)
```

## Admin Interfaces

### InvoiceAdmin
- **List**: invoice_number, tenant_id, status, total, issued_at, due_at
- **Filters**: status, issued_at, due_at, created_at
- **Read-only**: Created via service layer only
- **Inline**: Line items displayed

### PaymentAdmin
- **List**: id, tenant_id, invoice, gateway, status, amount, created_at
- **Filters**: gateway, status, created_at
- **Read-only**: Created via service layer only

## Repository Pattern

### InvoiceRepository
```python
get_by_id(invoice_id) → Optional[Invoice]
get_by_invoice_number(invoice_number) → Optional[Invoice]
list_by_tenant(tenant_id, limit=100) → List[Invoice]
save(invoice) → Invoice
delete(invoice_id) → bool
```

### PaymentRepository
```python
get_by_id(payment_id) → Optional[Payment]
get_by_invoice(invoice_id) → List[Payment]
list_by_tenant(tenant_id, limit=100) → List[Payment]
save(payment) → Payment
delete(payment_id) → bool
```

## Integration Points

### With Pricing Module
- Retrieve plan details for invoice generation
- Get pricing rules for overage calculations

### With Subscription Module
- Get active subscription for billing period
- Determine plan code for invoice

### With Quota Module
- Retrieve usage data for overage calculation
- Generate invoices from usage events

## Usage Examples

### Generate Invoice from Subscription
```python
from core.billing.services.use_cases import InvoiceService

service = InvoiceService(invoice_repo)

# Calculate from usage
invoice = service.calculate_invoice_from_usage(
    tenant_id=tenant.id,
    billing_cycle=BillingCycle(start_date, end_date),
    usage_data={
        "tracked_products": 550,  # Over 500 limit
        "price_updates": 1200
    }
)

# Issue invoice
invoice = service.issue_invoice(invoice.id, due_days=14)
```

### Process Payment
```python
from core.billing.services.use_cases import PaymentService
from core.billing.domain.value_objects import PaymentGateway

payment_service = PaymentService(payment_repo, invoice_repo)

# Initiate
result = payment_service.initiate_payment(
    tenant_id=tenant.id,
    invoice_id=invoice.id,
    gateway=PaymentGateway.STRIPE,
    gateway_config={"api_key": settings.STRIPE_API_KEY}
)

# Redirect user to result["redirect_url"]

# Webhook/callback verifies payment
payment = payment_service.verify_payment(
    payment_id=result["payment_id"],
    gateway_config={"api_key": settings.STRIPE_API_KEY}
)
```

## File Structure

```
core/billing/
├── domain/
│   ├── entities.py           # Invoice, Payment aggregates
│   ├── value_objects.py      # Money, InvoiceLineItem, BillingCycle, enums
│   └── exceptions.py         # BillingError hierarchy
├── repositories/
│   ├── interfaces.py         # InvoiceRepository, PaymentRepository ABCs
│   └── implementations.py    # InMemory implementations for testing
├── infrastructure/
│   ├── django_models.py      # InvoiceModel, PaymentModel, LineItemModel
│   ├── adapters.py           # DjangoORM repository implementations
│   └── admin.py              # Admin interfaces
├── services/
│   ├── payment_gateway.py    # Gateway abstraction + implementations
│   └── use_cases.py          # InvoiceService, PaymentService
├── migrations/
│   └── 0001_initial.py       # Database schema
└── apps.py                   # BillingConfig
```

## Database Schema

**Tables Created**: 3
- `billing_invoice`
- `billing_invoice_line_item`
- `billing_payment`

**Indexes Created**: 7
- InvoiceModel: 3 indexes
- PaymentModel: 4 indexes

**Schemas Updated**: 52 (public + 51 tenants)

## Configuration

**settings.py**:
```python
SHARED_APPS = [
    ...
    'core.billing.apps.BillingConfig',
    ...
]
```

**Payment Gateway Config** (example):
```python
PAYMENT_GATEWAYS = {
    "stripe": {
        "api_key": env("STRIPE_API_KEY"),
        "webhook_secret": env("STRIPE_WEBHOOK_SECRET"),
    },
    "payos": {
        "api_key": env("PAYOS_API_KEY"),
        "client_id": env("PAYOS_CLIENT_ID"),
    },
    "vnpay": {
        "terminal_id": env("VNPAY_TERMINAL_ID"),
        "secret_key": env("VNPAY_SECRET_KEY"),
    }
}
```

## Testing

### In-Memory Repositories
```python
from core.billing.repositories.implementations import (
    InMemoryInvoiceRepository,
    InMemoryPaymentRepository
)

invoice_repo = InMemoryInvoiceRepository()
payment_repo = InMemoryPaymentRepository()
```

### Example Test
```python
def test_invoice_lifecycle():
    repo = InMemoryInvoiceRepository()
    service = InvoiceService(repo)
    
    # Create draft
    invoice = service.create_invoice(tenant_id, billing_cycle, line_items)
    assert invoice.status == InvoiceStatus.DRAFT
    
    # Issue
    invoice = service.issue_invoice(invoice.id)
    assert invoice.status == InvoiceStatus.PENDING
    assert invoice.invoice_number.startswith("INV-")
    
    # Pay
    invoice = service.mark_invoice_paid(invoice.id)
    assert invoice.status == InvoiceStatus.PAID
```

## Future Enhancements

### Phase 1 (Runtime Flow Integration)
- [ ] Complete Stripe API integration
- [ ] Complete PayOS API integration
- [ ] Complete VNPay API integration
- [ ] Webhook handlers for payment verification
- [ ] Email notifications for invoices

### Phase 2 (Advanced Features)
- [ ] Recurring billing automation
- [ ] Invoice templates (PDF generation)
- [ ] Payment retry logic
- [ ] Dunning management
- [ ] Multi-currency support
- [ ] Tax calculation service integration

### Phase 3 (Reporting & Analytics)
- [ ] Revenue reports
- [ ] Payment success rates
- [ ] Overdue invoice tracking
- [ ] Gateway performance comparison

## Deployment Status

**Infrastructure**: ✅ Complete
**Migrations**: ✅ Applied (52/52 schemas)
**Admin**: ✅ Registered
**Services**: ✅ Implemented (placeholders)
**Gateway Integration**: ⏳ Placeholders only
**Runtime Flow**: ⏳ Not implemented
**Tests**: ⏳ Not implemented

## Notes

- **Temporary Implementation**: Module structure is complete but gateway integrations are placeholders
- **No Runtime Flow**: Payment gateways return mock data, not connected to actual APIs
- **Production Readiness**: Infrastructure ready; requires gateway integration before production use
- **Security**: Gateway credentials must be stored securely (environment variables, secrets manager)

---

**Module Complete**: ✅ Infrastructure & Structure  
**Next Steps**: Integrate actual payment gateway APIs when ready for production
