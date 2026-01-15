from datetime import date
from uuid import uuid4

from core.subscription.domain.entities import Subscription
from core.subscription.domain.value_objects import DateRange, SubscriptionStatus
from core.subscription.repositories.implementations import InMemorySubscriptionRepository
from core.subscription.services.use_cases import SubscriptionManagementService


def test_service_get_active_subscription():
    tenant_id = uuid4()
    repository = InMemorySubscriptionRepository()
    service = SubscriptionManagementService(repository)

    date_range = DateRange(start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    subscription = Subscription.new(
        tenant_id=tenant_id,
        plan_code="starter",
        date_range=date_range,
        status=SubscriptionStatus.ACTIVE,
    )
    repository.save(subscription)

    result = service.get_active_subscription(tenant_id)

    assert result.plan_code == "starter"
    assert result.status == "active"


def test_service_tenant_subscriptions_list():
    tenant_id = uuid4()
    repository = InMemorySubscriptionRepository()
    service = SubscriptionManagementService(repository)

    date_range1 = DateRange(start_date=date(2025, 1, 1), end_date=date(2025, 12, 31))
    date_range2 = DateRange(start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))

    sub1 = Subscription.new(
        tenant_id=tenant_id,
        plan_code="starter",
        date_range=date_range1,
        status=SubscriptionStatus.EXPIRED,
    )
    sub2 = Subscription.new(
        tenant_id=tenant_id,
        plan_code="growth",
        date_range=date_range2,
        status=SubscriptionStatus.ACTIVE,
    )

    repository.save(sub1)
    repository.save(sub2)

    results = service.get_tenant_subscriptions(tenant_id)

    assert len(results) == 2
    assert results[0].plan_code in ("starter", "growth")
