from __future__ import annotations

from typing import Dict, Iterable, Optional
from uuid import UUID

from core.subscription.domain.entities import Subscription
from core.subscription.repositories.interfaces import SubscriptionRepository


class InMemorySubscriptionRepository(SubscriptionRepository):
    """Simple in-memory repository useful for tests."""

    def __init__(self) -> None:
        self._storage: Dict[UUID, Subscription] = {}

    def list_by_tenant(self, tenant_id: UUID) -> Iterable[Subscription]:
        return [sub for sub in self._storage.values() if sub.tenant_id == tenant_id]

    def get_by_id(self, subscription_id: UUID) -> Optional[Subscription]:
        return self._storage.get(subscription_id)

    def get_active_by_tenant(self, tenant_id: UUID) -> Optional[Subscription]:
        for sub in self._storage.values():
            if sub.tenant_id == tenant_id and sub.is_active():
                return sub
        return None

    def save(self, subscription: Subscription) -> Subscription:
        self._storage[subscription.id] = subscription
        return subscription

    def delete(self, subscription: Subscription) -> None:
        self._storage.pop(subscription.id, None)
