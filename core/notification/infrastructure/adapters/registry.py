"""Provider adapter factory and registry."""
import logging
from typing import Dict, Optional

from core.notification.domain.exceptions import SenderNotFoundError
from core.notification.infrastructure.adapters.base import NotificationProviderAdapter
from core.notification.infrastructure.adapters.trapmail import TrapmailAdapter

logger = logging.getLogger(__name__)


class ProviderAdapterRegistry:
    """
    Registry for notification provider adapters.
    
    Maps sender_key → adapter instance.
    Admin must configure providers via Django Admin / YAML before use.
    """
    
    def __init__(self):
        """Initialize registry with built-in adapters."""
        self._adapters: Dict[str, NotificationProviderAdapter] = {}
        self._register_builtin_adapters()
    
    def _register_builtin_adapters(self) -> None:
        """Register built-in adapters."""
        self.register("trapmail_verify", TrapmailAdapter())
        # TODO: Register other providers as they're implemented
        # self.register("sendgrid_primary", SendGridAdapter())
        # self.register("twilio_sms", TwilioAdapter())
        logger.info(f"[Adapter Registry] Registered {len(self._adapters)} built-in adapters")
    
    def register(self, sender_key: str, adapter: NotificationProviderAdapter) -> None:
        """
        Register an adapter for a provider.
        
        Args:
            sender_key: Unique key (e.g., 'trapmail_verify', 'sendgrid_primary')
            adapter: NotificationProviderAdapter instance
        """
        self._adapters[sender_key] = adapter
        logger.info(f"[Adapter Registry] Registered adapter for sender_key='{sender_key}'")
    
    def get(self, sender_key: str) -> NotificationProviderAdapter:
        """
        Get adapter for a provider.
        
        Args:
            sender_key: Unique key from NotificationSender.sender_key
        
        Returns:
            Adapter instance
        
        Raises:
            SenderNotFoundError: If sender_key not registered
        """
        if sender_key not in self._adapters:
            available_keys = ", ".join(self._adapters.keys())
            raise SenderNotFoundError(
                f"Provider adapter not configured: sender_key='{sender_key}'. "
                f"Available adapters: [{available_keys}]. "
                f"Please register the adapter or contact admin to configure the provider."
            )
        
        return self._adapters[sender_key]
    
    def list_providers(self) -> list:
        """Get list of registered sender keys."""
        return list(self._adapters.keys())


# Global registry instance
_registry = ProviderAdapterRegistry()


def get_adapter(sender_key: str) -> NotificationProviderAdapter:
    """Get adapter for a sender key."""
    return _registry.get(sender_key)


def register_adapter(sender_key: str, adapter: NotificationProviderAdapter) -> None:
    """Register a new adapter."""
    _registry.register(sender_key, adapter)


def list_registered_providers() -> list:
    """List all registered sender keys."""
    return _registry.list_providers()
