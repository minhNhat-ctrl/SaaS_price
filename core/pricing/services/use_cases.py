from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List, Optional

from core.pricing.domain.entities import Plan
from core.pricing.domain.exceptions import PlanNotFoundError
from core.pricing.domain.value_objects import BillingCycle, Money, PlanLimit, PricingRule
from core.pricing.repositories.interfaces import PlanRepository

_DEFAULT_PLAN_DEFINITIONS: List[Dict] = [
    {
        "code": "starter",
        "name": "Starter",
        "description": "Free tier for evaluation and small projects.",
        "currency": "USD",
        "amount": Decimal("0"),
        "billing_cycle": BillingCycle.MONTHLY,
        "limits": [
            {"code": "tracked_products", "description": "Tracked product URLs per tenant", "value": 50, "period": "per_month"},
            {"code": "price_updates", "description": "Price updates per day", "value": 500, "period": "per_day"},
        ],
        "pricing_rules": [],
    },
    {
        "code": "growth",
        "name": "Growth",
        "description": "Business tier with higher limits and email alerts.",
        "currency": "USD",
        "amount": Decimal("149"),
        "billing_cycle": BillingCycle.MONTHLY,
        "limits": [
            {"code": "tracked_products", "description": "Tracked product URLs per tenant", "value": 1000, "period": "per_month"},
            {"code": "price_updates", "description": "Price updates per day", "value": 15000, "period": "per_day"},
            {"code": "team_members", "description": "Team seats", "value": 10, "period": None},
        ],
        "pricing_rules": [
            {
                "name": "price_update_overage",
                "rule_type": "overage",
                "configuration": {
                    "metric": "price_updates",
                    "unit_price": "0.02",
                    "included": "15000",
                },
            }
        ],
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "description": "Custom limits, SLA, and priority support.",
        "currency": "USD",
        "amount": Decimal("399"),
        "billing_cycle": BillingCycle.MONTHLY,
        "limits": [
            {"code": "tracked_products", "description": "Tracked product URLs per tenant", "value": 5000, "period": "per_month"},
            {"code": "price_updates", "description": "Price updates per day", "value": 100000, "period": "per_day"},
            {"code": "team_members", "description": "Team seats", "value": 25, "period": None},
        ],
        "pricing_rules": [
            {
                "name": "custom_contract_pricing",
                "rule_type": "contract",
                "configuration": {
                    "notes": "Contact sales for tailored pricing",
                },
            }
        ],
    },
]


@dataclass
class PlanDTO:
    code: str
    name: str
    description: str
    currency: str
    amount: Decimal
    billing_cycle: str
    limits: List[Dict]
    pricing_rules: List[Dict]
    is_active: bool
    metadata: Dict[str, str]

    @staticmethod
    def from_plan(plan: Plan) -> "PlanDTO":
        return PlanDTO(
            code=plan.code,
            name=plan.name,
            description=plan.description,
            currency=plan.price.currency,
            amount=plan.price.amount,
            billing_cycle=plan.billing_cycle.value,
            limits=[
                {
                    "code": limit.code,
                    "description": limit.description,
                    "value": limit.value,
                    "period": limit.period,
                }
                for limit in plan.limits
            ],
            pricing_rules=[
                {
                    "name": rule.name,
                    "rule_type": rule.rule_type,
                    "configuration": rule.configuration,
                }
                for rule in plan.pricing_rules
            ],
            is_active=plan.is_active,
            metadata=plan.metadata,
        )


class PlanFactory:
    """Factory for producing Plan aggregates from definition payloads."""

    @staticmethod
    def from_definition(payload: Dict) -> Plan:
        limits = [
            PlanLimit(
                code=limit["code"],
                description=limit.get("description", ""),
                value=int(limit.get("value", 0)),
                period=limit.get("period"),
            )
            for limit in payload.get("limits", [])
        ]
        rules = [
            PricingRule(
                name=rule["name"],
                rule_type=rule.get("rule_type", ""),
                configuration=rule.get("configuration", {}),
            )
            for rule in payload.get("pricing_rules", [])
        ]
        plan = Plan.new(
            code=payload["code"],
            name=payload["name"],
            description=payload.get("description", ""),
            price=Money(amount=payload["amount"], currency=payload["currency"]),
            billing_cycle=payload["billing_cycle"],
            limits=limits,
            pricing_rules=rules,
            metadata=payload.get("metadata", {}),
        )
        return plan


class PlanCatalogService:
    """Application service orchestrating plan retrieval and default definitions."""

    def __init__(self, repository: PlanRepository) -> None:
        self.repository = repository

    def list_active_plans(self) -> List[PlanDTO]:
        plans = [PlanDTO.from_plan(plan) for plan in self.repository.list_all() if plan.is_active]
        if plans:
            return plans
        return [PlanDTO.from_plan(PlanFactory.from_definition(defn)) for defn in _DEFAULT_PLAN_DEFINITIONS]

    def get_plan(self, code: str) -> PlanDTO:
        plan = self.repository.get_by_code(code)
        if plan:
            return PlanDTO.from_plan(plan)
        for definition in _DEFAULT_PLAN_DEFINITIONS:
            if definition["code"] == code:
                return PlanDTO.from_plan(PlanFactory.from_definition(definition))
        raise PlanNotFoundError(f"Plan with code '{code}' not found")

    def ensure_default_plans(self) -> None:
        """Ensure repository contains default plans. Intended for admin bootstrap flows."""
        existing_codes = {plan.code for plan in self.repository.list_all()}
        for definition in _DEFAULT_PLAN_DEFINITIONS:
            if definition["code"] in existing_codes:
                continue
            plan = PlanFactory.from_definition(definition)
            self.repository.save(plan)
