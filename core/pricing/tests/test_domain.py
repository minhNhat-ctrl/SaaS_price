from decimal import Decimal

import pytest

from core.pricing.domain.entities import Plan
from core.pricing.domain.value_objects import BillingCycle, Money, PlanLimit, PricingRule


def test_plan_activation_toggle():
    plan = Plan.new(
        code="starter",
        name="Starter",
        description="",
        price=Money(amount=Decimal("0"), currency="USD"),
        billing_cycle=BillingCycle.MONTHLY,
    )
    plan.deactivate()
    assert plan.is_active is False
    plan.activate()
    assert plan.is_active is True


def test_limit_validation():
    with pytest.raises(ValueError):
        PlanLimit(code="tracked_products", description="", value=-1)


def test_pricing_rule_serialization_roundtrip():
    plan = Plan.new(
        code="growth",
        name="Growth",
        description="",
        price=Money(amount=Decimal("149"), currency="USD"),
        billing_cycle=BillingCycle.MONTHLY,
        limits=[PlanLimit(code="tracked_products", description="", value=1000)],
        pricing_rules=[PricingRule(name="overage", rule_type="overage", configuration={"metric": "tracked_products"})],
    )
    assert plan.pricing_rules[0].configuration["metric"] == "tracked_products"
