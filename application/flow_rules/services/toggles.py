"""Application services for querying flow toggles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..domain.entities import FlowRuleToggle
from ..repositories.interfaces import FlowRuleToggleRepository


@dataclass
class FlowToggleService:
    """Provides toggle resolution for application flows."""

    repository: FlowRuleToggleRepository

    def is_step_enabled(self, flow_code: str, step_code: str) -> bool:
        toggle = self.repository.get_toggle(flow_code, step_code)
        if toggle is None:
            return True
        return toggle.is_enabled

    def set_step_toggle(self, flow_code: str, step_code: str, enabled: bool, description: str = "") -> FlowRuleToggle:
        toggle = FlowRuleToggle(flow_code=flow_code, step_code=step_code, is_enabled=enabled, description=description or None)
        return self.repository.set_toggle(toggle)


# Global service instance (lazy singleton)
_service: Optional[FlowToggleService] = None


def get_flow_toggle_service() -> FlowToggleService:
    """Get or create the flow toggle service (lazy singleton)."""
    global _service
    if _service is None:
        from ..repositories.implementations import DjangoFlowRuleToggleRepository
        repo = DjangoFlowRuleToggleRepository()
        _service = FlowToggleService(repository=repo)
    return _service
