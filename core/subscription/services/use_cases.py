from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from core.subscription.domain.entities import Subscription
from core.subscription.domain.exceptions import SubscriptionNotFoundError
from core.subscription.domain.value_objects import DateRange, SubscriptionStatus
from core.subscription.repositories.interfaces import SubscriptionRepository


@dataclass
class SubscriptionDTO:
    """Data transfer object for subscription responses."""

    id: str
    tenant_id: str
    plan_code: str
    status: str
    start_date: str
    end_date: str
    created_at: str
    updated_at: str

    @staticmethod
    def from_subscription(subscription: Subscription) -> "SubscriptionDTO":
        return SubscriptionDTO(
            id=str(subscription.id),
            tenant_id=str(subscription.tenant_id),
            plan_code=subscription.plan_code,
            status=subscription.status.value,
            start_date=subscription.date_range.start_date.isoformat(),
            end_date=subscription.date_range.end_date.isoformat(),
            created_at=subscription.created_at.isoformat(),
            updated_at=subscription.updated_at.isoformat(),
        )


class SubscriptionManagementService:
    """Application service for subscription lifecycle."""

    def __init__(self, repository: SubscriptionRepository) -> None:
        self.repository = repository

    def get_tenant_subscriptions(self, tenant_id: UUID) -> List[SubscriptionDTO]:
        """List all subscriptions for a tenant."""
        subscriptions = self.repository.list_by_tenant(tenant_id)
        return [SubscriptionDTO.from_subscription(sub) for sub in subscriptions]

    def get_active_subscription(self, tenant_id: UUID) -> SubscriptionDTO:
        """Get the currently active subscription for a tenant."""
        subscription = self.repository.get_active_by_tenant(tenant_id)
        if not subscription:
            raise SubscriptionNotFoundError(f"No active subscription found for tenant {tenant_id}")
        return SubscriptionDTO.from_subscription(subscription)

    def activate_subscription(self, subscription_id: UUID) -> SubscriptionDTO:
        """Transition a subscription to ACTIVE."""
        subscription = self.repository.get_by_id(subscription_id)
        if not subscription:
            raise SubscriptionNotFoundError(f"Subscription {subscription_id} not found")
        subscription.activate()
        saved = self.repository.save(subscription)
        return SubscriptionDTO.from_subscription(saved)

    def suspend_subscription(self, subscription_id: UUID) -> SubscriptionDTO:
        """Transition a subscription to SUSPENDED."""
        subscription = self.repository.get_by_id(subscription_id)
        if not subscription:
            raise SubscriptionNotFoundError(f"Subscription {subscription_id} not found")
        subscription.suspend()
        saved = self.repository.save(subscription)
        return SubscriptionDTO.from_subscription(saved)

    def expire_subscription(self, subscription_id: UUID) -> SubscriptionDTO:
        """Transition a subscription to EXPIRED."""
        subscription = self.repository.get_by_id(subscription_id)
        if not subscription:
            raise SubscriptionNotFoundError(f"Subscription {subscription_id} not found")
        subscription.expire()
        saved = self.repository.save(subscription)
        return SubscriptionDTO.from_subscription(saved)
