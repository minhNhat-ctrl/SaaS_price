from typing import Optional, List
from datetime import datetime
import uuid

from core.quota.domain.entities import UsageRecord, QuotaLimit
from core.quota.domain.value_objects import UsageEvent
from core.quota.repositories.interfaces import UsageRepository
from core.quota.infrastructure.django_models import UsageRecordModel, UsageEventModel


class DjangoORMUsageRepository(UsageRepository):
    """Repository implementation mapping UsageRecordModel ↔ UsageRecord domain entity."""

    @staticmethod
    def _model_to_entity(model: UsageRecordModel) -> UsageRecord:
        """Convert ORM model to domain entity."""
        return UsageRecord(
            id=model.id,
            tenant_id=model.tenant_id,
            metric_code=model.metric_code,
            current_usage=model.current_usage,
            period_start=model.period_start,
            period_end=model.period_end,
        )

    @staticmethod
    def _entity_to_model(entity: UsageRecord) -> UsageRecordModel:
        """Convert domain entity to ORM model."""
        return UsageRecordModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            metric_code=entity.metric_code,
            current_usage=entity.current_usage,
            period_start=entity.period_start,
            period_end=entity.period_end,
        )

    def list_by_tenant_and_metric(
        self, tenant_id: uuid.UUID, metric_code: str
    ) -> List[UsageRecord]:
        """Retrieve all usage records for a tenant and metric."""
        models = UsageRecordModel.objects.filter(tenant_id=tenant_id, metric_code=metric_code).order_by(
            "-period_end"
        )
        return [self._model_to_entity(m) for m in models]

    def get_current_period(
        self, tenant_id: uuid.UUID, metric_code: str, period_end: datetime
    ) -> Optional[UsageRecord]:
        """Get active usage record for current billing period."""
        try:
            model = UsageRecordModel.objects.get(
                tenant_id=tenant_id, metric_code=metric_code, period_end=period_end
            )
            return self._model_to_entity(model)
        except UsageRecordModel.DoesNotExist:
            return None

    def get_by_id(self, record_id: uuid.UUID) -> Optional[UsageRecord]:
        """Retrieve usage record by ID."""
        try:
            model = UsageRecordModel.objects.get(id=record_id)
            return self._model_to_entity(model)
        except UsageRecordModel.DoesNotExist:
            return None

    def save(self, entity: UsageRecord) -> UsageRecord:
        """Persist usage record to database."""
        model = self._entity_to_model(entity)
        model.save()
        return self._model_to_entity(model)

    def delete(self, record_id: uuid.UUID) -> bool:
        """Delete usage record (audit only, should rarely be called)."""
        try:
            UsageRecordModel.objects.get(id=record_id).delete()
            return True
        except UsageRecordModel.DoesNotExist:
            return False

    def get_for_period(
        self, tenant_id: uuid.UUID, period_start: datetime, period_end: datetime
    ) -> List[UsageRecord]:
        """Retrieve all usage records for a tenant within date range."""
        models = UsageRecordModel.objects.filter(
            tenant_id=tenant_id,
            period_start__gte=period_start,
            period_end__lte=period_end,
        ).order_by("-period_end")
        return [self._model_to_entity(m) for m in models]


class UsageEventRecorder:
    """Records immutable usage events for audit trail."""

    @staticmethod
    def record(tenant_id: uuid.UUID, event: UsageEvent, metadata: dict = None) -> None:
        """Record a usage event with optional context metadata."""
        UsageEventModel.objects.create(
            tenant_id=tenant_id,
            metric_code=event.metric_code,
            amount=event.amount,
            metadata=metadata or {},
        )

    @staticmethod
    def get_events_for_metric(
        tenant_id: uuid.UUID, metric_code: str, limit: int = 100
    ) -> List[UsageEventModel]:
        """Retrieve recent usage events for a metric."""
        return UsageEventModel.objects.filter(tenant_id=tenant_id, metric_code=metric_code).order_by(
            "-created_at"
        )[:limit]
