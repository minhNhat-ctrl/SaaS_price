from __future__ import annotations

from datetime import date
from django.db import models
from django.utils import timezone

import uuid


class SubscriptionModel(models.Model):
    """Django ORM model backing the Subscription aggregate."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)  # Reference to Tenant (not FK to avoid circular deps)
    plan_code = models.CharField(max_length=64)  # Reference to Plan.code
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=16,
        choices=[
            ("trial", "Trial"),
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("expired", "Expired"),
        ],
        default="trial",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscription_subscription"
        ordering = ["-created_at"]
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "start_date", "end_date"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"Tenant {self.tenant_id} → {self.plan_code} ({self.status})"
