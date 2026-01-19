from datetime import date, datetime
from uuid import UUID

from core.subscription.api.serializers import SubscriptionSerializer
from core.subscription.domain.value_objects import SubscriptionStatus
from core.subscription.dto import SubscriptionSummary


def test_subscription_serializer():
    dto = SubscriptionSummary(
        id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        tenant_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
        plan_code="growth",
        status=SubscriptionStatus.ACTIVE,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        updated_at=datetime(2026, 1, 1, 0, 0, 0),
    )

    data = SubscriptionSerializer.from_dto(dto)

    assert data["plan_code"] == "growth"
    assert data["status"] == "active"
    assert data["tenant_id"] == "550e8400-e29b-41d4-a716-446655440001"
