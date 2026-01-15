from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from .value_objects import LimitEnforcement, UsageEvent


@dataclass
class UsageRecord:
    """Records a tenant's usage of a specific metric within a period."""

    id: UUID
    tenant_id: UUID
    metric_code: str
    current_usage: int
    period_start: datetime
    period_end: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @staticmethod
    def new(
        tenant_id: UUID,
        metric_code: str,
        period_start: datetime,
        period_end: datetime,
        initial_usage: int = 0,
    ) -> "UsageRecord":
        return UsageRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            metric_code=metric_code,
            current_usage=initial_usage,
            period_start=period_start,
            period_end=period_end,
        )

    def record_usage(self, event: UsageEvent) -> None:
        """Record a usage event and increment current usage."""
        if event.metric_code != self.metric_code:
            raise ValueError(f"Event metric {event.metric_code} does not match record {self.metric_code}")
        self.current_usage += event.amount
        self.updated_at = datetime.utcnow()

    def reset(self) -> None:
        """Reset usage to zero (e.g. on period boundary)."""
        self.current_usage = 0
        self.updated_at = datetime.utcnow()


@dataclass
class QuotaLimit:
    """Represents a plan's quota limit for a specific metric."""

    metric_code: str
    limit_value: int
    enforcement: LimitEnforcement
    description: str = ""

    def __post_init__(self) -> None:
        if not self.metric_code:
            raise ValueError("metric_code is required")
        if self.limit_value < 0:
            raise ValueError("limit_value must be non-negative")

    def is_exceeded(self, current_usage: int) -> bool:
        """Check if current usage exceeds the limit."""
        return current_usage > self.limit_value

    def should_enforce(self) -> bool:
        """Check if this limit should be enforced."""
        return self.enforcement == LimitEnforcement.HARD
