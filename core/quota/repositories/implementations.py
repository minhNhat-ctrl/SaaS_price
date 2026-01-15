from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, Optional, Tuple
from uuid import UUID

from core.quota.domain.entities import UsageRecord
from core.quota.repositories.interfaces import UsageRepository


class InMemoryUsageRepository(UsageRepository):
    """Simple in-memory repository useful for tests."""

    def __init__(self) -> None:
        self._storage: Dict[UUID, UsageRecord] = {}

    def list_by_tenant_and_metric(self, tenant_id: UUID, metric_code: str) -> Iterable[UsageRecord]:
        return [
            rec for rec in self._storage.values()
            if rec.tenant_id == tenant_id and rec.metric_code == metric_code
        ]

    def get_current_period(self, tenant_id: UUID, metric_code: str, period_end: datetime) -> Optional[UsageRecord]:
        now = datetime.utcnow()
        for rec in self._storage.values():
            if (rec.tenant_id == tenant_id and
                rec.metric_code == metric_code and
                rec.period_start <= now <= rec.period_end):
                return rec
        return None

    def get_by_id(self, record_id: UUID) -> Optional[UsageRecord]:
        return self._storage.get(record_id)

    def save(self, usage_record: UsageRecord) -> UsageRecord:
        self._storage[usage_record.id] = usage_record
        return usage_record

    def delete(self, usage_record: UsageRecord) -> None:
        self._storage.pop(usage_record.id, None)
