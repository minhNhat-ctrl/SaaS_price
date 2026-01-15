from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable, Optional
from uuid import UUID

from core.quota.domain.entities import UsageRecord


class UsageRepository(ABC):
    """Repository contract for persisting UsageRecord aggregates."""

    @abstractmethod
    def list_by_tenant_and_metric(self, tenant_id: UUID, metric_code: str) -> Iterable[UsageRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_current_period(self, tenant_id: UUID, metric_code: str, period_end: datetime) -> Optional[UsageRecord]:
        """Get usage record for current period (end_date > now)."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, record_id: UUID) -> Optional[UsageRecord]:
        raise NotImplementedError

    @abstractmethod
    def save(self, usage_record: UsageRecord) -> UsageRecord:
        raise NotImplementedError

    @abstractmethod
    def delete(self, usage_record: UsageRecord) -> None:
        raise NotImplementedError
