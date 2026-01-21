"""DTO contracts for the Quota module ↔ application boundary."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from core.quota.domain.entities import QuotaLimit, UsageRecord
from core.quota.domain.value_objects import LimitEnforcement


@dataclass
class UsagePeriodDTO:
    """Represents the billing window for quota tracking."""

    start: datetime
    end: datetime


@dataclass
class QuotaLimitDTO:
    """Quota limit descriptor provided by the Pricing module."""

    metric_code: str
    limit_value: int
    enforcement: LimitEnforcement = LimitEnforcement.NONE
    description: str = ""

    @classmethod
    def from_domain(cls, limit: QuotaLimit) -> "QuotaLimitDTO":
        return cls(
            metric_code=limit.metric_code,
            limit_value=limit.limit_value,
            enforcement=limit.enforcement,
            description=limit.description,
        )

    def to_domain(self) -> QuotaLimit:
        return QuotaLimit(
            metric_code=self.metric_code,
            limit_value=self.limit_value,
            enforcement=self.enforcement,
            description=self.description,
        )


@dataclass
class UsageRecordCommand:
    """Command payload instructing the service to record usage."""

    tenant_id: UUID
    metric_code: str
    period: UsagePeriodDTO
    amount: int = 1
    limit: Optional[QuotaLimitDTO] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.metric_code:
            raise ValueError("metric_code is required")
        if self.amount <= 0:
            raise ValueError("amount must be positive")


@dataclass
class UsageSnapshotQuery:
    """Query payload requesting usage metrics for a tenant in a period."""

    tenant_id: UUID
    period: UsagePeriodDTO
    metric_codes: Optional[List[str]] = None
    limits: List[QuotaLimitDTO] = field(default_factory=list)


@dataclass
class QuotaCheckQuery:
    """Dry-run command to check quota allowance before consuming."""

    tenant_id: UUID
    metric_code: str
    requested_amount: int
    period: UsagePeriodDTO
    limit: Optional[QuotaLimitDTO] = None

    def validate(self) -> None:
        if not self.metric_code:
            raise ValueError("metric_code is required")
        if self.requested_amount <= 0:
            raise ValueError("requested_amount must be positive")


def _remaining_value(current_usage: int, limit: Optional[QuotaLimit]) -> Optional[int]:
    if not limit:
        return None
    remaining = limit.limit_value - current_usage
    return remaining if remaining >= 0 else 0


def _status_label(current_usage: int, limit: Optional[QuotaLimit]) -> str:
    if not limit:
        return "no_limit"
    if current_usage > limit.limit_value:
        return "over_limit"
    if current_usage == limit.limit_value:
        return "at_limit"
    return "within_limit"


@dataclass
class UsageStatusDTO:
    """Snapshot of a metric's usage relative to its limit."""

    tenant_id: UUID
    metric_code: str
    current: int
    limit: Optional[int]
    remaining: Optional[int]
    enforcement: LimitEnforcement
    status: str
    period_start: datetime
    period_end: datetime

    @classmethod
    def from_usage_record(
        cls,
        record: UsageRecord,
        limit: Optional[QuotaLimit] = None,
    ) -> "UsageStatusDTO":
        limit_value = limit.limit_value if limit else None
        return cls(
            tenant_id=record.tenant_id,
            metric_code=record.metric_code,
            current=record.current_usage,
            limit=limit_value,
            remaining=_remaining_value(record.current_usage, limit),
            enforcement=limit.enforcement if limit else LimitEnforcement.NONE,
            status=_status_label(record.current_usage, limit),
            period_start=record.period_start,
            period_end=record.period_end,
        )

    @classmethod
    def empty(
        cls,
        tenant_id: UUID,
        metric_code: str,
        period: UsagePeriodDTO,
        limit: Optional[QuotaLimit] = None,
    ) -> "UsageStatusDTO":
        limit_value = limit.limit_value if limit else None
        return cls(
            tenant_id=tenant_id,
            metric_code=metric_code,
            current=0,
            limit=limit_value,
            remaining=_remaining_value(0, limit),
            enforcement=limit.enforcement if limit else LimitEnforcement.NONE,
            status=_status_label(0, limit),
            period_start=period.start,
            period_end=period.end,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_code": self.metric_code,
            "current": self.current,
            "limit": self.limit,
            "remaining": self.remaining,
            "enforcement": self.enforcement.value,
            "status": self.status,
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
        }


@dataclass
class QuotaCheckResult:
    """Result DTO describing whether a usage request is allowed."""

    metric_code: str
    current: int
    requested: int
    after_action: int
    limit: Optional[int]
    enforcement: LimitEnforcement
    would_exceed: bool
    allowed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_code": self.metric_code,
            "current": self.current,
            "requested": self.requested,
            "after_action": self.after_action,
            "limit": self.limit,
            "enforcement": self.enforcement.value,
            "would_exceed": self.would_exceed,
            "allowed": self.allowed,
        }


@dataclass
class UsageSnapshotDTO:
    """Aggregate snapshot across metrics for a tenant."""

    tenant_id: UUID
    period_start: datetime
    period_end: datetime
    metrics: List[UsageStatusDTO] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": str(self.tenant_id),
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
            "metrics": [metric.to_dict() for metric in self.metrics],
        }


__all__ = [
    "UsagePeriodDTO",
    "QuotaLimitDTO",
    "UsageRecordCommand",
    "UsageSnapshotQuery",
    "QuotaCheckQuery",
    "UsageStatusDTO",
    "QuotaCheckResult",
    "UsageSnapshotDTO",
]
