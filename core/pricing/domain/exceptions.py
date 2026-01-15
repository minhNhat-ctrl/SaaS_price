class PricingDomainError(Exception):
    """Base exception for pricing domain."""


class PlanNotFoundError(PricingDomainError):
    """Raised when requested plan cannot be located."""


class InvalidPlanStateError(PricingDomainError):
    """Raised when plan data violates domain rules."""
