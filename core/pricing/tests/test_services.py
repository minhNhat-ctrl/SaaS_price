from decimal import Decimal

from core.pricing.domain.value_objects import BillingCycle, Money, PlanLimit, PricingRule
from core.pricing.domain.entities import Plan
from core.pricing.repositories.implementations import InMemoryPlanRepository
from core.pricing.services.use_cases import PlanCatalogService, PlanDTO


def test_service_returns_default_definitions_when_repository_empty():
    repository = InMemoryPlanRepository()
    service = PlanCatalogService(repository)

    plans = service.list_active_plans()

    assert isinstance(plans, list)
    assert plans  # defaults returned
    assert all(isinstance(plan, PlanDTO) for plan in plans)


def test_service_uses_repository_data_when_available():
    repository = InMemoryPlanRepository()
    plan = Plan.new(
        code="custom",
        name="Custom",
        description="Custom plan",
        price=Money(amount=Decimal("25"), currency="USD"),
        billing_cycle=BillingCycle.MONTHLY,
        limits=[PlanLimit(code="tracked_products", description="", value=200)],
        pricing_rules=[PricingRule(name="extra", rule_type="overage", configuration={"unit_price": "0.10"})],
    )
    repository.save(plan)

    service = PlanCatalogService(repository)

    plans = service.list_active_plans()

    assert len(plans) == 1
    assert plans[0].code == "custom"


def test_ensure_default_plans_persists_definitions():
    repository = InMemoryPlanRepository()
    service = PlanCatalogService(repository)

    service.ensure_default_plans()

    persisted_codes = {plan.code for plan in repository.list_all()}
    assert {"starter", "growth", "enterprise"}.issubset(persisted_codes)
