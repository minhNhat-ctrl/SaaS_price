"""Repository implementations for flow rule toggles."""
from __future__ import annotations

from typing import Optional

from ..domain.entities import FlowRuleToggle
from .interfaces import FlowRuleToggleRepository
from ..infrastructure.django_models import FlowRuleToggleModel


class DjangoFlowRuleToggleRepository(FlowRuleToggleRepository):
    """Django-backed repository for flow rule toggles."""

    def get_toggle(self, flow_code: str, step_code: str) -> Optional[FlowRuleToggle]:
        try:
            instance = FlowRuleToggleModel.objects.get(
                flow_code=flow_code.strip().lower(),
                step_code=step_code.strip().lower(),
            )
        except FlowRuleToggleModel.DoesNotExist:
            return None
        return FlowRuleToggle(
            flow_code=instance.flow_code,
            step_code=instance.step_code,
            is_enabled=instance.is_enabled,
            description=instance.description or None,
        )

    def set_toggle(self, toggle: FlowRuleToggle) -> FlowRuleToggle:
        instance, _ = FlowRuleToggleModel.objects.update_or_create(
            flow_code=toggle.normalized_flow(),
            step_code=toggle.normalized_step(),
            defaults={
                "is_enabled": toggle.is_enabled,
                "description": toggle.description or "",
            },
        )
        return FlowRuleToggle(
            flow_code=instance.flow_code,
            step_code=instance.step_code,
            is_enabled=instance.is_enabled,
            description=instance.description or None,
        )
