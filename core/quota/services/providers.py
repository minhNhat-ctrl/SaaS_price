"""Factory helpers for wiring Quota services."""
from __future__ import annotations

from typing import Optional

from core.quota.infrastructure.adapters import DjangoORMUsageRepository, UsageEventRecorder
from core.quota.repositories.interfaces import UsageRepository
from core.quota.services.use_cases import QuotaEnforcementService, UsageTrackingService

__all__ = [
    "get_usage_tracking_service",
    "get_quota_enforcement_service",
]


def get_usage_tracking_service(
    repository: Optional[UsageRepository] = None,
    event_recorder: Optional[UsageEventRecorder] = None,
) -> UsageTrackingService:
    """Provision a UsageTrackingService with default infrastructure wiring."""

    repo = repository or DjangoORMUsageRepository()
    recorder = event_recorder or UsageEventRecorder()
    return UsageTrackingService(repository=repo, event_recorder=recorder)


def get_quota_enforcement_service(
    repository: Optional[UsageRepository] = None,
) -> QuotaEnforcementService:
    """Provision a QuotaEnforcementService for dry-run checks."""

    repo = repository or DjangoORMUsageRepository()
    return QuotaEnforcementService(repository=repo)
