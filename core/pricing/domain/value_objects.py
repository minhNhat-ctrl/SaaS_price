from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional


class BillingCycle(Enum):
    """Supported billing cycles."""

    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass(frozen=True)
class Money:
    """Simple value object representing a monetary amount."""

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if self.amount < Decimal("0"):
            raise ValueError("Money amount cannot be negative")
        if not self.currency:
            raise ValueError("Currency code is required")


@dataclass(frozen=True)
class PlanLimit:
    """Represents one limit that a plan enforces."""

    code: str
    description: str
    value: int
    period: Optional[str] = None  # e.g. per_month, per_day

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("Limit value must be non-negative")
        if not self.code:
            raise ValueError("Limit code is required")


@dataclass(frozen=True)
class PricingRule:
    """Pricing adjustment rule applied on top of base price."""

    name: str
    rule_type: str
    configuration: Dict[str, str]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Pricing rule name is required")
        if not self.rule_type:
            raise ValueError("Pricing rule type is required")
