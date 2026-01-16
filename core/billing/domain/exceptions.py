class BillingError(Exception):
    """Base exception for billing operations."""
    pass


class InvoiceNotFoundError(BillingError):
    """Raised when invoice cannot be found."""
    def __init__(self, invoice_id):
        self.invoice_id = invoice_id
        super().__init__(f"Invoice not found: {invoice_id}")


class PaymentNotFoundError(BillingError):
    """Raised when payment cannot be found."""
    def __init__(self, payment_id):
        self.payment_id = payment_id
        super().__init__(f"Payment not found: {payment_id}")


class InvalidInvoiceStateError(BillingError):
    """Raised when invoice state transition is invalid."""
    def __init__(self, current_status, attempted_action):
        self.current_status = current_status
        self.attempted_action = attempted_action
        super().__init__(f"Cannot {attempted_action} invoice in {current_status} state")


class PaymentGatewayError(BillingError):
    """Raised when payment gateway operation fails."""
    def __init__(self, gateway, message):
        self.gateway = gateway
        super().__init__(f"{gateway} error: {message}")


class InvoiceCalculationError(BillingError):
    """Raised when invoice calculation fails."""
    pass
