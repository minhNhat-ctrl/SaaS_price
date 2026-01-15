from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LimitEnforcement(Enum):
    """How strictly to enforce a quota limit."""

    HARD = "hard"  # Reject action if over limit
    SOFT = "soft"  # Warn but allow action
    NONE = "none"  # Track but don't enforce


@dataclass(frozen=True)
class UsageEvent:
    """Immutable event representing a usage occurrence."""

    metric_code: str
    amount: int = 1  # Quantity consumed

    def __post_init__(self) -> None:
        if not self.metric_code:
            raise ValueError("metric_code is required")
        if self.amount <= 0:
            raise ValueError("amount must be positive")
