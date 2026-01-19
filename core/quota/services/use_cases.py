"""Application services orchestrating quota tracking and enforcement."""
from __future__ import annotations

from typing import Dict, List, Optional

from core.quota.domain.entities import QuotaLimit, UsageRecord
from core.quota.domain.exceptions import QuotaExceededError
from core.quota.domain.value_objects import LimitEnforcement, UsageEvent
from core.quota.dto import (
    QuotaCheckQuery,
    QuotaCheckResult,
    QuotaLimitDTO,
    UsageRecordCommand,
    UsageSnapshotDTO,
    UsageSnapshotQuery,
    UsageStatusDTO,
)
from core.quota.infrastructure.adapters import UsageEventRecorder
from core.quota.repositories.interfaces import UsageRepository


def _limit_from_dto(limit_dto: Optional[QuotaLimitDTO]) -> Optional[QuotaLimit]:
    return limit_dto.to_domain() if limit_dto else None


class UsageTrackingService:
    """Service responsible for recording usage events and producing snapshots."""

    def __init__(
        self,
        repository: UsageRepository,
        event_recorder: Optional[UsageEventRecorder] = None,
    ) -> None:
        self.repository = repository
        self.event_recorder = event_recorder or UsageEventRecorder()

    def record_usage(self, command: UsageRecordCommand) -> UsageStatusDTO:
        command.validate()
        period = command.period
        record = self.repository.get_current_period(command.tenant_id, command.metric_code, period.end)
        if record is None:
            record = UsageRecord.new(
                tenant_id=command.tenant_id,
                metric_code=command.metric_code,
                period_start=period.start,
                period_end=period.end,
            )

        limit = _limit_from_dto(command.limit)
        projected_total = record.current_usage + command.amount
        if limit and limit.is_exceeded(projected_total) and limit.should_enforce():
            raise QuotaExceededError(
                metric_code=command.metric_code,
                current=projected_total,
                limit=limit.limit_value,
            )

        event = UsageEvent(metric_code=command.metric_code, amount=command.amount)
        record.record_usage(event)
        saved_record = self.repository.save(record)
        if self.event_recorder:
            self.event_recorder.record(command.tenant_id, event, metadata=command.metadata)

        return UsageStatusDTO.from_usage_record(saved_record, limit=limit)

    def get_usage_snapshot(self, query: UsageSnapshotQuery) -> UsageSnapshotDTO:
        period = query.period
        limit_map: Dict[str, QuotaLimit] = {
            limit.metric_code: limit.to_domain() for limit in query.limits
        }
        metric_codes: List[str] = query.metric_codes or list(limit_map.keys())
        statuses: List[UsageStatusDTO] = []

        for metric_code in metric_codes:
            record = self.repository.get_current_period(query.tenant_id, metric_code, period.end)
            limit = limit_map.get(metric_code)
            if record:
                statuses.append(UsageStatusDTO.from_usage_record(record, limit=limit))
            else:
                statuses.append(
                    UsageStatusDTO.empty(
                        tenant_id=query.tenant_id,
                        metric_code=metric_code,
                        period=period,
                        limit=limit,
                    )
                )

        return UsageSnapshotDTO(
            tenant_id=query.tenant_id,
            period_start=period.start,
            period_end=period.end,
            metrics=statuses,
        )


class QuotaEnforcementService:
    """Service performing dry-run checks before mutating usage."""

    def __init__(self, repository: UsageRepository) -> None:
        self.repository = repository

    def check_quota(self, query: QuotaCheckQuery) -> QuotaCheckResult:
        query.validate()
        period = query.period
        record = self.repository.get_current_period(query.tenant_id, query.metric_code, period.end)
        current_usage = record.current_usage if record else 0
        limit = _limit_from_dto(query.limit)
        after_action = current_usage + query.requested_amount

        would_exceed = False
        allowed = True
        enforcement = limit.enforcement if limit else LimitEnforcement.NONE
        if limit:
            would_exceed = limit.is_exceeded(after_action)
            if would_exceed and limit.should_enforce():
                allowed = False

        return QuotaCheckResult(
            metric_code=query.metric_code,
            current=current_usage,
            requested=query.requested_amount,
            after_action=after_action,
            limit=limit.limit_value if limit else None,
            enforcement=enforcement,
            would_exceed=would_exceed,
            allowed=allowed,
        )
