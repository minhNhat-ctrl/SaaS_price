from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from .value_objects import DateRange, SubscriptionStatus


@dataclass
class Subscription:
    """Represents a tenant's subscription to a plan for a specific time period."""

    id: UUID
    tenant_id: UUID
    plan_code: str
    date_range: DateRange
    status: SubscriptionStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @staticmethod
    def new(
        tenant_id: UUID,
        plan_code: str,
        date_range: DateRange,
        status: SubscriptionStatus = SubscriptionStatus.TRIAL,
    ) -> "Subscription":
        return Subscription(
            id=uuid4(),
            tenant_id=tenant_id,
            plan_code=plan_code,
            date_range=date_range,
            status=status,
        )

    def activate(self) -> None:
        """Transition subscription to ACTIVE."""
        self.status = SubscriptionStatus.ACTIVE
        self.updated_at = datetime.utcnow()

    def suspend(self) -> None:
        """Transition subscription to SUSPENDED."""
        self.status = SubscriptionStatus.SUSPENDED
        self.updated_at = datetime.utcnow()

    def expire(self) -> None:
        """Transition subscription to EXPIRED."""
        self.status = SubscriptionStatus.EXPIRED
        self.updated_at = datetime.utcnow()

    def is_active(self) -> bool:
        """Check if subscription is in active state and within date range."""
        return self.status == SubscriptionStatus.ACTIVE
