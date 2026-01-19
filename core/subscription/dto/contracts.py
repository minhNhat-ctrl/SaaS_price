"""DTO contracts mediating Subscription module ↔ application interactions."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from core.subscription.domain.entities import Subscription
from core.subscription.domain.value_objects import SubscriptionStatus


@dataclass(slots=True)
class SubscriptionProvisionCommand:
    """Command payload for provisioning or renewing a subscription."""

    tenant_id: UUID
    plan_code: str
    start_date: date
    end_date: date
    initial_status: SubscriptionStatus = SubscriptionStatus.TRIAL


@dataclass(slots=True)
class SubscriptionListQuery:
    """Query payload for retrieving tenant subscriptions."""

    tenant_id: UUID
    status: Optional[SubscriptionStatus] = None


@dataclass(slots=True)
class ActiveSubscriptionQuery:
    """Query payload for requesting the active subscription of a tenant."""

    tenant_id: UUID


@dataclass(slots=True)
class SubscriptionLifecycleCommand:
    """Command for status transitions on an existing subscription."""

    subscription_id: UUID


@dataclass(slots=True)
class SubscriptionSummary:
    """DTO returned to the application/HTTP layer with subscription attributes."""

    id: UUID
    tenant_id: UUID
    plan_code: str
    status: SubscriptionStatus
    start_date: date
    end_date: date
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, subscription: Subscription) -> "SubscriptionSummary":
        return cls(
            id=subscription.id,
            tenant_id=subscription.tenant_id,
            plan_code=subscription.plan_code,
            status=subscription.status,
            start_date=subscription.date_range.start_date,
            end_date=subscription.date_range.end_date,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )
