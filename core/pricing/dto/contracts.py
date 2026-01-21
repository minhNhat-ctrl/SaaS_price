"""DTO contracts for Pricing module ↔ application interactions."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.pricing.domain.entities import Plan
from core.pricing.domain.value_objects import BillingCycle, PlanLimit, PricingRule


@dataclass
class PlanLimitDTO:
    code: str
    description: str
    value: int
    period: Optional[str] = None

    @classmethod
    def from_domain(cls, limit: PlanLimit) -> "PlanLimitDTO":
        return cls(
            code=limit.code,
            description=limit.description,
            value=limit.value,
            period=limit.period,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "description": self.description,
            "value": self.value,
            "period": self.period,
        }


@dataclass
class PlanPricingRuleDTO:
    name: str
    rule_type: str
    configuration: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_domain(cls, rule: PricingRule) -> "PlanPricingRuleDTO":
        return cls(
            name=rule.name,
            rule_type=rule.rule_type,
            configuration=dict(rule.configuration or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "rule_type": self.rule_type,
            "configuration": self.configuration,
        }


@dataclass
class PlanSummary:
    code: str
    name: str
    description: str
    currency: str
    amount: Decimal
    billing_cycle: BillingCycle
    limits: List[PlanLimitDTO] = field(default_factory=list)
    pricing_rules: List[PlanPricingRuleDTO] = field(default_factory=list)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_domain(cls, plan: Plan) -> "PlanSummary":
        return cls(
            code=plan.code,
            name=plan.name,
            description=plan.description,
            currency=plan.price.currency,
            amount=plan.price.amount,
            billing_cycle=plan.billing_cycle,
            limits=[PlanLimitDTO.from_domain(limit) for limit in plan.limits],
            pricing_rules=[PlanPricingRuleDTO.from_domain(rule) for rule in plan.pricing_rules],
            is_active=plan.is_active,
            metadata=dict(plan.metadata or {}),
        )


@dataclass
class PlanCatalogQuery:
    include_inactive: bool = False
    fallback_to_defaults: bool = True


@dataclass
class PlanLookupQuery:
    plan_code: str
    allow_default_fallback: bool = True


@dataclass
class PlanCatalogBootstrapCommand:
    include_codes: Optional[List[str]] = None

    def should_include(self, code: str) -> bool:
        if self.include_codes is None:
            return True
        return code in self.include_codes
