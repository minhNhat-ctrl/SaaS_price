"""Base adapter interface for notification providers."""
from abc import ABC, abstractmethod
from typing import Optional

from core.notification.domain.entities import NotificationSender
from core.notification.domain.value_objects import Channel


class NotificationProviderAdapter(ABC):
    """
    Abstract base class for notification provider adapters.
    
    Each provider (SendGrid, Twilio, Trapmail, etc.) implements this interface.
    The adapter is responsible for the actual send operation via the provider's API/service.
    """
    
    @abstractmethod
    def send(
        self,
        sender: NotificationSender,
        recipient: str,
        subject: str,
        body: str,
        channel: Channel,
        context: dict,
    ) -> Optional[str]:
        """
        Send notification via this provider.
        
        Args:
            sender: NotificationSender entity with provider config
            recipient: Email/phone/token/URL
            subject: Subject line (for EMAIL)
            body: Message body/content
            channel: Channel enum (EMAIL, SMS, PUSH, WEBHOOK)
            context: Original context dict for provider-specific metadata
        
        Returns:
            External message ID from provider (e.g., SendGrid message_id)
        
        Raises:
            NotificationSendError: If send fails
        """
        pass
