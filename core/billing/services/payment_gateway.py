from abc import ABC, abstractmethod
from typing import Dict, Optional
import uuid

from core.billing.domain.entities import Payment
from core.billing.domain.value_objects import Money, PaymentGateway


class PaymentGatewayInterface(ABC):
    """Abstract interface for payment gateway integration."""
    
    @abstractmethod
    def create_payment_intent(
        self,
        amount: Money,
        metadata: Dict = None
    ) -> Dict:
        """
        Create payment intent with gateway.
        
        Returns:
            Dict with 'transaction_id', 'redirect_url', 'status'
        """
        pass
    
    @abstractmethod
    def verify_payment(
        self,
        transaction_id: str
    ) -> Dict:
        """
        Verify payment status with gateway.
        
        Returns:
            Dict with 'status', 'amount', 'completed_at'
        """
        pass
    
    @abstractmethod
    def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Money] = None
    ) -> Dict:
        """
        Refund payment.
        
        Returns:
            Dict with 'refund_id', 'status', 'amount'
        """
        pass


class StripeGateway(PaymentGatewayInterface):
    """Stripe payment gateway implementation (placeholder)."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def create_payment_intent(self, amount: Money, metadata: Dict = None) -> Dict:
        """Create Stripe payment intent (not implemented)."""
        # TODO: Integrate with Stripe API
        return {
            "transaction_id": f"stripe_{uuid.uuid4().hex[:16]}",
            "redirect_url": "https://checkout.stripe.com/...",
            "status": "pending",
        }
    
    def verify_payment(self, transaction_id: str) -> Dict:
        """Verify Stripe payment (not implemented)."""
        # TODO: Integrate with Stripe API
        return {
            "status": "success",
            "amount": 0,
            "completed_at": None,
        }
    
    def refund_payment(self, transaction_id: str, amount: Optional[Money] = None) -> Dict:
        """Refund Stripe payment (not implemented)."""
        # TODO: Integrate with Stripe API
        return {
            "refund_id": f"refund_{uuid.uuid4().hex[:16]}",
            "status": "success",
            "amount": 0,
        }


class PayOSGateway(PaymentGatewayInterface):
    """PayOS payment gateway implementation (placeholder)."""
    
    def __init__(self, api_key: str, client_id: str):
        self.api_key = api_key
        self.client_id = client_id
    
    def create_payment_intent(self, amount: Money, metadata: Dict = None) -> Dict:
        """Create PayOS payment intent (not implemented)."""
        # TODO: Integrate with PayOS API
        return {
            "transaction_id": f"payos_{uuid.uuid4().hex[:16]}",
            "redirect_url": "https://pay.payos.vn/...",
            "status": "pending",
        }
    
    def verify_payment(self, transaction_id: str) -> Dict:
        """Verify PayOS payment (not implemented)."""
        # TODO: Integrate with PayOS API
        return {
            "status": "success",
            "amount": 0,
            "completed_at": None,
        }
    
    def refund_payment(self, transaction_id: str, amount: Optional[Money] = None) -> Dict:
        """Refund PayOS payment (not implemented)."""
        # TODO: Integrate with PayOS API
        return {
            "refund_id": f"refund_{uuid.uuid4().hex[:16]}",
            "status": "success",
            "amount": 0,
        }


class VNPayGateway(PaymentGatewayInterface):
    """VNPay payment gateway implementation (placeholder)."""
    
    def __init__(self, terminal_id: str, secret_key: str):
        self.terminal_id = terminal_id
        self.secret_key = secret_key
    
    def create_payment_intent(self, amount: Money, metadata: Dict = None) -> Dict:
        """Create VNPay payment intent (not implemented)."""
        # TODO: Integrate with VNPay API
        return {
            "transaction_id": f"vnpay_{uuid.uuid4().hex[:16]}",
            "redirect_url": "https://sandbox.vnpayment.vn/...",
            "status": "pending",
        }
    
    def verify_payment(self, transaction_id: str) -> Dict:
        """Verify VNPay payment (not implemented)."""
        # TODO: Integrate with VNPay API
        return {
            "status": "success",
            "amount": 0,
            "completed_at": None,
        }
    
    def refund_payment(self, transaction_id: str, amount: Optional[Money] = None) -> Dict:
        """Refund VNPay payment (not implemented)."""
        # TODO: Integrate with VNPay API
        return {
            "refund_id": f"refund_{uuid.uuid4().hex[:16]}",
            "status": "success",
            "amount": 0,
        }


class PaymentGatewayFactory:
    """Factory for creating payment gateway instances."""
    
    @staticmethod
    def create(gateway: PaymentGateway, config: Dict) -> PaymentGatewayInterface:
        """Create payment gateway instance based on type."""
        if gateway == PaymentGateway.STRIPE:
            return StripeGateway(api_key=config.get("api_key"))
        elif gateway == PaymentGateway.PAYOS:
            return PayOSGateway(
                api_key=config.get("api_key"),
                client_id=config.get("client_id")
            )
        elif gateway == PaymentGateway.VNPAY:
            return VNPayGateway(
                terminal_id=config.get("terminal_id"),
                secret_key=config.get("secret_key")
            )
        else:
            raise ValueError(f"Unsupported gateway: {gateway}")
