from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Optional
from uuid import UUID

from core.subscription.domain.entities import Subscription


class SubscriptionRepository(ABC):
    """Repository contract for persisting Subscription aggregates."""

    @abstractmethod
    def list_by_tenant(self, tenant_id: UUID) -> Iterable[Subscription]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, subscription_id: UUID) -> Optional[Subscription]:
        raise NotImplementedError

    @abstractmethod
    def get_active_by_tenant(self, tenant_id: UUID) -> Optional[Subscription]:
        """Get the currently active subscription for a tenant (if any)."""
        raise NotImplementedError

    @abstractmethod
    def save(self, subscription: Subscription) -> Subscription:
        raise NotImplementedError

    @abstractmethod
    def delete(self, subscription: Subscription) -> None:
        raise NotImplementedError
