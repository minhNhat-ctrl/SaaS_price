"""Notification value objects."""
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional


class Channel(str, Enum):
    """Notification delivery channel."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"


class SendStatus(str, Enum):
    """Notification send result status."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"


@dataclass
class SendCommand:
    """
    Command from Application to Notification module.
    
    Application decides WHAT to send and HOW.
    Notification executes the command.
    """
    
    template_key: str
    """Template identifier (e.g., billing.payment_failed)."""
    
    channel: Channel
    """Delivery channel (email, sms, etc.)."""
    
    recipient: str
    """Recipient address (email, phone, etc.)."""
    
    language: str = "en"
    """Template language (en, vi, etc.)."""
    
    context: Dict[str, Any] = None
    """Jinja2 template context for rendering."""
    
    sender_key: Optional[str] = None
    """Optional sender identifier. If None, use default sender for channel."""
    
    def __post_init__(self):
        if not self.template_key:
            raise ValueError("template_key cannot be empty")
        if not self.recipient:
            raise ValueError("recipient cannot be empty")
        if self.context is None:
            self.context = {}
