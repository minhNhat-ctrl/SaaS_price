from datetime import date
from uuid import uuid4

import pytest

from core.subscription.domain.entities import Subscription
from core.subscription.domain.value_objects import DateRange, SubscriptionStatus


def test_subscription_activation_transition():
    tenant_id = uuid4()
    date_range = DateRange(start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    subscription = Subscription.new(
        tenant_id=tenant_id,
        plan_code="growth",
        date_range=date_range,
        status=SubscriptionStatus.TRIAL,
    )
    assert subscription.status == SubscriptionStatus.TRIAL

    subscription.activate()
    assert subscription.status == SubscriptionStatus.ACTIVE
    assert subscription.is_active() is True


def test_subscription_suspension():
    tenant_id = uuid4()
    date_range = DateRange(start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    subscription = Subscription.new(
        tenant_id=tenant_id,
        plan_code="growth",
        date_range=date_range,
        status=SubscriptionStatus.ACTIVE,
    )
    subscription.suspend()
    assert subscription.status == SubscriptionStatus.SUSPENDED
    assert subscription.is_active() is False


def test_date_range_validation():
    with pytest.raises(ValueError):
        DateRange(start_date=date(2026, 12, 31), end_date=date(2026, 1, 1))


def test_date_range_contains_check():
    date_range = DateRange(start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    assert date_range.is_active_on(date(2026, 6, 15)) is True
    assert date_range.is_active_on(date(2025, 12, 31)) is False
    assert date_range.is_active_on(date(2027, 1, 1)) is False
