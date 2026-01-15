from decimal import Decimal

from core.pricing.api.serializers import PlanSerializer
from core.pricing.services.use_cases import PlanDTO


def test_plan_serializer_output():
    dto = PlanDTO(
        code="starter",
        name="Starter",
        description="",
        currency="USD",
        amount=Decimal("0"),
        billing_cycle="monthly",
        limits=[{"code": "tracked_products", "description": "", "value": 50, "period": "per_month"}],
        pricing_rules=[],
        is_active=True,
        metadata={},
    )

    data = PlanSerializer.from_service(dto)

    assert data["code"] == "starter"
    assert data["amount"] == Decimal("0")
    assert data["billing_cycle"] == "monthly"
    assert data["limits"][0]["value"] == 50
