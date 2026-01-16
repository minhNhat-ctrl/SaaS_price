"""Notification domain entities."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from .value_objects import Channel, SendStatus


@dataclass
class NotificationSender:
    """
    Notification sender configuration.
    
    Represents a mail/SMS provider with credentials.
    """
    
    id: UUID
    provider: str  # smtp, sendgrid, twilio, etc.
    channel: Channel
    from_email: Optional[str] = None  # For EMAIL channel
    from_name: Optional[str] = None
    credentials: Dict[str, Any] = None  # Encrypted in DB
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None
    
    def is_ready(self) -> bool:
        """Check if sender is configured and active."""
        return self.is_active and self.credentials is not None


@dataclass
class NotificationTemplate:
    """
    Notification template.
    
    Stores template for specific channel & language.
    Application decides WHETHER to send; Template only WHAT to send.
    """
    
    id: UUID
    template_key: str  # e.g., billing.payment_failed
    channel: Channel
    language: str  # en, vi, etc.
    subject: str  # For EMAIL: email subject
    body: str  # Jinja2 template with {{placeholders}}
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None
    
    def render(self, context: Dict[str, Any]) -> tuple[str, str]:
        """
        Render template with context.
        
        Returns: (subject, body)
        Raises: TemplateRenderError
        """
        from jinja2 import Template, TemplateError
        from .exceptions import TemplateRenderError
        
        try:
            subject_tpl = Template(self.subject)
            body_tpl = Template(self.body)
            
            rendered_subject = subject_tpl.render(context)
            rendered_body = body_tpl.render(context)
            
            return rendered_subject, rendered_body
        except TemplateError as e:
            raise TemplateRenderError(
                f"Failed to render template {self.template_key}: {str(e)}"
            )


@dataclass
class NotificationLog:
    """
    Notification send log (audit trail).
    
    Records every send attempt for monitoring & debugging.
    """
    
    id: UUID
    template_key: str
    channel: Channel
    recipient: str
    status: SendStatus
    error_message: Optional[str] = None
    external_id: Optional[str] = None  # Provider's message ID
    sent_at: Optional[datetime] = None
    created_at: datetime = None
    
    def is_successful(self) -> bool:
        return self.status == SendStatus.SENT
