"""Domain entities for application flow toggles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FlowRuleToggle:
    """Represents a boolean toggle for a specific flow step."""

    flow_code: str
    step_code: str
    is_enabled: bool = True
    description: Optional[str] = None

    def normalized_flow(self) -> str:
        return self.flow_code.strip().lower()

    def normalized_step(self) -> str:
        return self.step_code.strip().lower()
