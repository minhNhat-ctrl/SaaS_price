class QuotaDomainError(Exception):
    """Base exception for quota domain."""


class QuotaExceededError(QuotaDomainError):
    """Raised when usage exceeds hard limit."""

    def __init__(self, metric_code: str, current: int, limit: int) -> None:
        self.metric_code = metric_code
        self.current = current
        self.limit = limit
        super().__init__(f"Quota exceeded for {metric_code}: {current} > {limit}")


class QuotaNotFoundError(QuotaDomainError):
    """Raised when quota configuration cannot be located."""


class UsageRecordNotFoundError(QuotaDomainError):
    """Raised when usage record cannot be located."""
