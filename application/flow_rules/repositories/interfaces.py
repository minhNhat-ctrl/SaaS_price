"""Repository interfaces for flow rule toggles."""
from __future__ import annotations

from typing import Optional, Protocol

from ..domain.entities import FlowRuleToggle


class FlowRuleToggleRepository(Protocol):
    """Persistence abstraction for flow rule toggles."""

    def get_toggle(self, flow_code: str, step_code: str) -> Optional[FlowRuleToggle]:
        ...

    def set_toggle(self, toggle: FlowRuleToggle) -> FlowRuleToggle:
        ...
