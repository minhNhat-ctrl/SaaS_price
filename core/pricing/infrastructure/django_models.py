from __future__ import annotations

from django.db import models
from django.utils import timezone

import uuid


class PlanModel(models.Model):
    """Django ORM model backing the pricing Plan aggregate."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    currency = models.CharField(max_length=8, default="USD")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    billing_cycle = models.CharField(max_length=16)
    limits = models.JSONField(default=list, blank=True)
    pricing_rules = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pricing_plan"
        ordering = ["-created_at"]
        verbose_name = "Plan"
        verbose_name_plural = "Plans"

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.name} ({self.code})"
