from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid

from core.billing.domain.value_objects import (
    BillingContractStatus,
    PaymentStatus,
    PaymentGateway,
    Money,
)
from core.billing.domain.exceptions import (
    InvalidContractStateError,
    BillingContractNotFoundError,
)


class BillingContract:
    """
    BillingContract aggregate root.
    
    Represents a payment contract (opaque to business logic).
    Does NOT contain plan, product, feature, usage, or limit info.
    Only: contract + payment status + periods.
    """
    
    def __init__(
        self,
        account_id: uuid.UUID,
        external_contract_ref: str,  # Opaque reference to other modules
        provider: PaymentGateway,
        status: BillingContractStatus = BillingContractStatus.PENDING,
        started_at: Optional[datetime] = None,
        current_period_end: Optional[datetime] = None,
        canceled_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        id: Optional[uuid.UUID] = None,
    ):
        self.id = id or uuid.uuid4()
        self.account_id = account_id
        self.external_contract_ref = external_contract_ref
        self.provider = provider
        self.status = status
        self.started_at = started_at or datetime.utcnow()
        self.current_period_end = current_period_end
        self.canceled_at = canceled_at
        self.metadata = metadata or {}

    def activate(self, period_end: datetime) -> None:
        """Transition: pending → active."""
        if self.status not in (BillingContractStatus.PENDING,):
            raise InvalidContractStateError(
                f"Cannot activate contract in {self.status} state"
            )
        self.status = BillingContractStatus.ACTIVE
        self.current_period_end = period_end

    def mark_past_due(self) -> None:
        """Transition: active → past_due."""
        if self.status != BillingContractStatus.ACTIVE:
            raise InvalidContractStateError(
                f"Cannot mark past_due contract in {self.status} state"
            )
        self.status = BillingContractStatus.PAST_DUE

    def mark_expired(self) -> None:
        """Transition: active/past_due → expired."""
        if self.status not in (BillingContractStatus.ACTIVE, BillingContractStatus.PAST_DUE):
            raise InvalidContractStateError(
                f"Cannot expire contract in {self.status} state"
            )
        self.status = BillingContractStatus.EXPIRED

    def cancel(self) -> None:
        """Transition: any → canceled."""
        self.status = BillingContractStatus.CANCELED
        self.canceled_at = datetime.utcnow()

    def can_transition_to(self, target_status: BillingContractStatus) -> bool:
        """Check if state transition is valid."""
        allowed_transitions = {
            BillingContractStatus.PENDING: [BillingContractStatus.ACTIVE, BillingContractStatus.CANCELED],
            BillingContractStatus.ACTIVE: [BillingContractStatus.PAST_DUE, BillingContractStatus.EXPIRED, BillingContractStatus.CANCELED],
            BillingContractStatus.PAST_DUE: [BillingContractStatus.ACTIVE, BillingContractStatus.EXPIRED, BillingContractStatus.CANCELED],
            BillingContractStatus.EXPIRED: [BillingContractStatus.CANCELED],
            BillingContractStatus.CANCELED: [],
        }
        return target_status in allowed_transitions.get(self.status, [])


class BillingProviderRef:
    """
    Maps BillingContract ↔ gateway provider objects.
    
    Allows:
    - 1 contract → multiple provider objects (migration scenario)
    - Track primary object
    - Audit history
    """
    
    def __init__(
        self,
        billing_contract_id: uuid.UUID,
        provider: PaymentGateway,
        provider_object_type: str,  # 'subscription', 'payment_intent', etc.
        provider_object_id: str,    # Stripe subscription ID, etc.
        is_primary: bool = True,
        id: Optional[uuid.UUID] = None,
    ):
        self.id = id or uuid.uuid4()
        self.billing_contract_id = billing_contract_id
        self.provider = provider
        self.provider_object_type = provider_object_type
        self.provider_object_id = provider_object_id
        self.is_primary = is_primary


class BillingPayment:
    """
    BillingPayment - minimal payment record for audit/support.
    
    Only captures: who paid, how much, when, status.
    NOT responsible for calculating amounts or determining eligibility.
    """
    
    def __init__(
        self,
        billing_contract_id: uuid.UUID,
        provider: PaymentGateway,
        provider_payment_id: str,
        amount: int,  # Stored in cents
        currency: str,
        status: PaymentStatus = PaymentStatus.PENDING,
        occurred_at: Optional[datetime] = None,
        raw_event_id: Optional[str] = None,
        id: Optional[uuid.UUID] = None,
    ):
        self.id = id or uuid.uuid4()
        self.billing_contract_id = billing_contract_id
        self.provider = provider
        self.provider_payment_id = provider_payment_id
        self.amount = amount
        self.currency = currency
        self.status = status
        self.occurred_at = occurred_at or datetime.utcnow()
        self.raw_event_id = raw_event_id

    def mark_success(self) -> None:
        """Mark payment as successful."""
        if self.status not in (PaymentStatus.PENDING, PaymentStatus.PROCESSING):
            raise InvalidContractStateError(f"Cannot mark {self.status} payment as success")
        self.status = PaymentStatus.SUCCESS

    def mark_failed(self) -> None:
        """Mark payment as failed."""
        if self.status not in (PaymentStatus.PENDING, PaymentStatus.PROCESSING):
            raise InvalidContractStateError(f"Cannot mark {self.status} payment as failed")
        self.status = PaymentStatus.FAILED

    def refund(self) -> None:
        """Mark payment as refunded."""
        if self.status != PaymentStatus.SUCCESS:
            raise InvalidContractStateError(f"Cannot refund {self.status} payment")
        self.status = PaymentStatus.REFUNDED


class BillingEvent:
    """
    Normalized webhook event from payment gateway.
    
    Provides:
    - Idempotency (payload_hash prevents duplicate processing)
    - Debug trail (what webhook we received and processed)
    - Replay capability (reprocess events if needed)
    """
    
    def __init__(
        self,
        provider: PaymentGateway,
        event_type: str,
        provider_event_id: str,
        payload_hash: str,
        billing_contract_id: Optional[uuid.UUID] = None,
        received_at: Optional[datetime] = None,
        processed_at: Optional[datetime] = None,
        id: Optional[uuid.UUID] = None,
    ):
        self.id = id or uuid.uuid4()
        self.provider = provider
        self.event_type = event_type
        self.provider_event_id = provider_event_id
        self.payload_hash = payload_hash
        self.billing_contract_id = billing_contract_id
        self.received_at = received_at or datetime.utcnow()
        self.processed_at = processed_at

    def mark_processed(self) -> None:
        """Mark event as processed."""
        self.processed_at = datetime.utcnow()


class BillingGatewayCustomer:
    """
    Maps account_id ↔ gateway customer.
    
    Allows:
    - Store customer metadata per provider
    - Track customer creation date
    - Support multi-provider accounts
    """
    
    def __init__(
        self,
        account_id: uuid.UUID,
        provider: PaymentGateway,
        provider_customer_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        id: Optional[uuid.UUID] = None,
    ):
        self.id = id or uuid.uuid4()
        self.account_id = account_id
        self.provider = provider
        self.provider_customer_id = provider_customer_id
        self.metadata = metadata or {}
