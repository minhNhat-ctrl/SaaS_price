from core.subscription.api.serializers import SubscriptionSerializer
from core.subscription.services.use_cases import SubscriptionDTO


def test_subscription_serializer():
    dto = SubscriptionDTO(
        id="550e8400-e29b-41d4-a716-446655440000",
        tenant_id="550e8400-e29b-41d4-a716-446655440001",
        plan_code="growth",
        status="active",
        start_date="2026-01-01",
        end_date="2026-12-31",
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )

    data = SubscriptionSerializer.from_dto(dto)

    assert data["plan_code"] == "growth"
    assert data["status"] == "active"
    assert data["tenant_id"] == "550e8400-e29b-41d4-a716-446655440001"
