from __future__ import annotations

from typing import List
from uuid import UUID

from core.subscription.domain.exceptions import SubscriptionNotFoundError
from core.subscription.dto import (
    ActiveSubscriptionQuery,
    SubscriptionLifecycleCommand,
    SubscriptionListQuery,
    SubscriptionSummary,
)
from core.subscription.repositories.interfaces import SubscriptionRepository


class SubscriptionManagementService:
    """Application service for subscription lifecycle."""

    def __init__(self, repository: SubscriptionRepository) -> None:
        self.repository = repository

    def get_tenant_subscriptions(self, query: SubscriptionListQuery) -> List[SubscriptionSummary]:
        """List all subscriptions for a tenant."""
        subscriptions = self.repository.list_by_tenant(query.tenant_id)
        summaries = [SubscriptionSummary.from_domain(sub) for sub in subscriptions]
        if query.status:
            summaries = [summary for summary in summaries if summary.status == query.status]
        return summaries

    def get_active_subscription(self, query: ActiveSubscriptionQuery) -> SubscriptionSummary:
        """Get the currently active subscription for a tenant."""
        subscription = self.repository.get_active_by_tenant(query.tenant_id)
        if not subscription:
            raise SubscriptionNotFoundError(f"No active subscription found for tenant {query.tenant_id}")
        return SubscriptionSummary.from_domain(subscription)

    def activate_subscription(self, command: SubscriptionLifecycleCommand) -> SubscriptionSummary:
        """Transition a subscription to ACTIVE."""
        subscription = self.repository.get_by_id(command.subscription_id)
        if not subscription:
            raise SubscriptionNotFoundError(f"Subscription {command.subscription_id} not found")
        subscription.activate()
        saved = self.repository.save(subscription)
        return SubscriptionSummary.from_domain(saved)

    def suspend_subscription(self, command: SubscriptionLifecycleCommand) -> SubscriptionSummary:
        """Transition a subscription to SUSPENDED."""
        subscription = self.repository.get_by_id(command.subscription_id)
        if not subscription:
            raise SubscriptionNotFoundError(f"Subscription {command.subscription_id} not found")
        subscription.suspend()
        saved = self.repository.save(subscription)
        return SubscriptionSummary.from_domain(saved)

    def expire_subscription(self, command: SubscriptionLifecycleCommand) -> SubscriptionSummary:
        """Transition a subscription to EXPIRED."""
        subscription = self.repository.get_by_id(command.subscription_id)
        if not subscription:
            raise SubscriptionNotFoundError(f"Subscription {command.subscription_id} not found")
        subscription.expire()
        saved = self.repository.save(subscription)
        return SubscriptionSummary.from_domain(saved)
