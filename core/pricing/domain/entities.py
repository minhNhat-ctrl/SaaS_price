from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from uuid import UUID, uuid4

from .value_objects import Money, PlanLimit, PricingRule, BillingCycle


@dataclass
class Plan:
    """Represents one SaaS subscription plan definition."""

    id: UUID
    code: str
    name: str
    description: str
    price: Money
    billing_cycle: BillingCycle
    limits: List[PlanLimit] = field(default_factory=list)
    pricing_rules: List[PricingRule] = field(default_factory=list)
    is_active: bool = True
    metadata: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("Plan code is required")
        if not self.name:
            raise ValueError("Plan name is required")

    @staticmethod
    def new(code: str, name: str, description: str, price: Money, billing_cycle: BillingCycle,
            limits: Optional[List[PlanLimit]] = None, pricing_rules: Optional[List[PricingRule]] = None,
            metadata: Optional[Dict[str, str]] = None) -> "Plan":
        return Plan(
            id=uuid4(),
            code=code,
            name=name,
            description=description,
            price=price,
            billing_cycle=billing_cycle,
            limits=limits or [],
            pricing_rules=pricing_rules or [],
            metadata=metadata or {},
        )

    def activate(self) -> None:
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def replace_limits(self, limits: List[PlanLimit]) -> None:
        self.limits = limits
        self.updated_at = datetime.utcnow()

    def replace_pricing_rules(self, rules: List[PricingRule]) -> None:
        self.pricing_rules = rules
        self.updated_at = datetime.utcnow()
