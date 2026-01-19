"""Factory helpers for wiring Subscription services."""
from __future__ import annotations

from typing import Optional

from core.subscription.infrastructure.adapters import DjangoORMSubscriptionRepository
from core.subscription.repositories.interfaces import SubscriptionRepository
from core.subscription.services.use_cases import SubscriptionManagementService

__all__ = ["get_subscription_service"]


def get_subscription_service(repository: Optional[SubscriptionRepository] = None) -> SubscriptionManagementService:
    """Return a SubscriptionManagementService with default repository wiring."""
    repo = repository or DjangoORMSubscriptionRepository()
    return SubscriptionManagementService(repository=repo)
