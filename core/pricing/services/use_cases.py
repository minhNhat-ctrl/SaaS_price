from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional

from core.pricing.domain.entities import Plan
from core.pricing.domain.exceptions import PlanNotFoundError
from core.pricing.domain.value_objects import BillingCycle, Money, PlanLimit, PricingRule
from core.pricing.repositories.interfaces import PlanRepository
from core.pricing.dto import (
    PlanCatalogBootstrapCommand,
    PlanCatalogQuery,
    PlanLookupQuery,
    PlanSummary,
)

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

    def list_active_plans(self, query: Optional[PlanCatalogQuery] = None) -> List[PlanSummary]:
        query = query or PlanCatalogQuery()
        plans = list(self.repository.list_all())
        if not query.include_inactive:
            plans = [plan for plan in plans if plan.is_active]

        summaries = [PlanSummary.from_domain(plan) for plan in plans]
        if summaries or not query.fallback_to_defaults:
            return summaries

        return [PlanSummary.from_domain(PlanFactory.from_definition(defn)) for defn in _DEFAULT_PLAN_DEFINITIONS]

    def get_plan(self, query: PlanLookupQuery) -> PlanSummary:
        plan = self.repository.get_by_code(query.plan_code)
        if plan:
            return PlanSummary.from_domain(plan)
        if query.allow_default_fallback:
            for definition in _DEFAULT_PLAN_DEFINITIONS:
                if definition["code"] == query.plan_code:
                    return PlanSummary.from_domain(PlanFactory.from_definition(definition))
        raise PlanNotFoundError(f"Plan with code '{query.plan_code}' not found")

    def ensure_default_plans(self, command: Optional[PlanCatalogBootstrapCommand] = None) -> None:
        """Ensure repository contains default plans. Intended for admin bootstrap flows."""
        command = command or PlanCatalogBootstrapCommand()
        existing_codes = {plan.code for plan in self.repository.list_all()}
        for definition in _DEFAULT_PLAN_DEFINITIONS:
            code = definition["code"]
            if code in existing_codes or not command.should_include(code):
                continue
            plan = PlanFactory.from_definition(definition)
            self.repository.save(plan)
