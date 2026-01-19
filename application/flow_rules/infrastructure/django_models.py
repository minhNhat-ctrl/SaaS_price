"""Django ORM model backing flow rule toggles."""
from __future__ import annotations

from django.db import models


class FlowRuleToggleModel(models.Model):
    """Stores whether a given flow step is enabled."""

    flow_code = models.CharField(max_length=64)
    step_code = models.CharField(max_length=64)
    is_enabled = models.BooleanField(default=True)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "app_flow_rule_toggle"
        unique_together = ("flow_code", "step_code")
        ordering = ("flow_code", "step_code")

    def save(self, *args, **kwargs):  # type: ignore[override]
        self.flow_code = (self.flow_code or "").strip().lower()
        self.step_code = (self.step_code or "").strip().lower()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.flow_code}:{self.step_code}"
