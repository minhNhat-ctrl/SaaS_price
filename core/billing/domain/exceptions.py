"""
Domain exceptions for Billing module.

Billing module handles contracts, payments, and events.
Does NOT contain plan, product, feature, usage, or limit validation.
"""


class BillingError(Exception):
    """Base billing domain exception."""
    pass


class BillingContractNotFoundError(BillingError):
    """Billing contract not found."""
    pass


class BillingPaymentNotFoundError(BillingError):
    """Billing payment not found."""
    pass


class BillingEventNotFoundError(BillingError):
    """Billing event not found."""
    pass


class BillingGatewayCustomerNotFoundError(BillingError):
    """Billing gateway customer not found."""
    pass


class InvalidContractStateError(BillingError):
    """Invalid contract state transition."""
    pass


class PaymentGatewayError(BillingError):
    """Payment gateway integration error."""
    pass


class WebhookSignatureError(BillingError):
    """Webhook signature validation failed."""
    pass


class DuplicateWebhookError(BillingError):
    """Webhook already processed (idempotency check)."""
    pass


class BillingProviderConfigNotFoundError(BillingError):
    """Billing provider config not found."""
    pass
