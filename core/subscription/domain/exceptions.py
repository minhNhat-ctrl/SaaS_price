class SubscriptionDomainError(Exception):
    """Base exception for subscription domain."""


class SubscriptionNotFoundError(SubscriptionDomainError):
    """Raised when requested subscription cannot be located."""


class InvalidSubscriptionStateError(SubscriptionDomainError):
    """Raised when subscription data violates domain rules."""
