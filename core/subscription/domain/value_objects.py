from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class SubscriptionStatus(Enum):
    """Supported subscription statuses."""

    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


@dataclass(frozen=True)
class DateRange:
    """Value object representing start/end date for a subscription."""

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")

    def is_active_on(self, check_date: date) -> bool:
        """Check if subscription is within date range."""
        return self.start_date <= check_date <= self.end_date
