from __future__ import annotations

from datetime import datetime
from django.db import models
from django.utils import timezone

import uuid


class UsageRecordModel(models.Model):
    """Django ORM model backing the UsageRecord aggregate."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)  # Reference to Tenant
    metric_code = models.CharField(max_length=64)  # e.g., 'tracked_products', 'price_updates'
    current_usage = models.IntegerField(default=0)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "quota_usage_record"
        ordering = ["-period_end", "-created_at"]
        verbose_name = "Usage Record"
        verbose_name_plural = "Usage Records"
        indexes = [
            models.Index(fields=["tenant_id", "metric_code", "period_end"]),
            models.Index(fields=["tenant_id", "period_end"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.tenant_id} / {self.metric_code}: {self.current_usage} (period: {self.period_start.date()})"


class UsageEventModel(models.Model):
    """Audit trail of individual usage events (immutable)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    metric_code = models.CharField(max_length=64)
    amount = models.IntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)  # Contextual info (e.g., what action triggered it)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "quota_usage_event"
        ordering = ["-created_at"]
        verbose_name = "Usage Event"
        verbose_name_plural = "Usage Events"
        indexes = [
            models.Index(fields=["tenant_id", "metric_code", "created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.tenant_id} / {self.metric_code}: +{self.amount}"
