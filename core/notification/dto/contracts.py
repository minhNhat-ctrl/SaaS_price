"""DTO contracts bridging Notification module with the application layer."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from core.notification.domain.entities import NotificationLog, NotificationSender, NotificationTemplate
from core.notification.domain.value_objects import Channel, SendCommand, SendStatus


@dataclass
class SendNotificationCommand:
    """Command payload issued by orchestrators when dispatching a notification."""

    template_key: str
    channel: Channel
    recipient: str
    language: str = "en"
    context: Dict[str, Any] = field(default_factory=dict)
    sender_key: Optional[str] = None

    def to_domain(self) -> SendCommand:
        return SendCommand(
            template_key=self.template_key,
            channel=self.channel,
            recipient=self.recipient,
            language=self.language,
            context=dict(self.context),
            sender_key=self.sender_key,
        )

    @classmethod
    def from_domain(cls, command: SendCommand) -> "SendNotificationCommand":
        return cls(
            template_key=command.template_key,
            channel=command.channel,
            recipient=command.recipient,
            language=command.language,
            context=dict(command.context or {}),
            sender_key=command.sender_key,
        )


@dataclass
class NotificationLogDTO:
    """Snapshot of a notification send attempt."""

    id: UUID
    template_key: str
    channel: Channel
    recipient: str
    status: SendStatus
    error_message: Optional[str]
    external_id: Optional[str]
    sender_key: Optional[str]
    sent_at: Optional[datetime]
    created_at: Optional[datetime]
    context: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_domain(cls, log: NotificationLog) -> "NotificationLogDTO":
        context_snapshot = getattr(log, "context", None)
        if context_snapshot is None:
            context_snapshot = getattr(log, "context_snapshot", {})
        sender_key = getattr(log, "sender_key", None)
        return cls(
            id=getattr(log, "id"),
            template_key=log.template_key,
            channel=log.channel,
            recipient=log.recipient,
            status=log.status,
            error_message=getattr(log, "error_message", None),
            external_id=getattr(log, "external_id", None),
            sender_key=sender_key,
            sent_at=getattr(log, "sent_at", None),
            created_at=getattr(log, "created_at", None),
            context=dict(context_snapshot or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "template_key": self.template_key,
            "channel": self.channel.value,
            "recipient": self.recipient,
            "status": self.status.value,
            "error_message": self.error_message,
            "external_id": self.external_id,
            "sender_key": self.sender_key,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "context": self.context,
        }


@dataclass
class NotificationSenderDTO:
    """Sender configuration summary for application use."""

    id: UUID
    provider: str
    channel: Channel
    is_active: bool
    sender_key: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None

    @classmethod
    def from_domain(cls, sender: NotificationSender) -> "NotificationSenderDTO":
        return cls(
            id=getattr(sender, "id"),
            provider=sender.provider,
            channel=sender.channel,
            is_active=sender.is_active,
            sender_key=getattr(sender, "sender_key", None),
            from_email=getattr(sender, "from_email", None),
            from_name=getattr(sender, "from_name", None),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "provider": self.provider,
            "channel": self.channel.value,
            "is_active": self.is_active,
            "sender_key": self.sender_key,
            "from_email": self.from_email,
            "from_name": self.from_name,
        }


@dataclass
class NotificationTemplateDTO:
    """Template projection for orchestrators selecting content."""

    id: UUID
    template_key: str
    channel: Channel
    language: str
    subject: str
    body: str
    is_active: bool
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_domain(cls, template: NotificationTemplate) -> "NotificationTemplateDTO":
        return cls(
            id=getattr(template, "id"),
            template_key=template.template_key,
            channel=template.channel,
            language=template.language,
            subject=template.subject,
            body=template.body,
            is_active=template.is_active,
            description=getattr(template, "description", None),
            created_at=getattr(template, "created_at", None),
            updated_at=getattr(template, "updated_at", None),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "template_key": self.template_key,
            "channel": self.channel.value,
            "language": self.language,
            "subject": self.subject,
            "body": self.body,
            "is_active": self.is_active,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class NotificationLogQuery:
    """Query parameters for listing notification logs."""

    template_key: Optional[str] = None
    channel: Optional[Channel] = None
    status: Optional[SendStatus] = None
    recipient: Optional[str] = None
    limit: int = 50


# ============================================================
# Specialized Email DTOs for Common Identity Notifications
# ============================================================


@dataclass
class VerificationEmailCommand:
    """Command to send email verification link."""
    
    recipient_email: str
    verification_token: str
    verification_url: str
    language: str = "en"
    sender_key: Optional[str] = None  # If None, use default
    
    def to_send_notification_command(self) -> SendNotificationCommand:
        """Convert to generic SendNotificationCommand."""
        return SendNotificationCommand(
            template_key="email_verification",
            channel=Channel.EMAIL,
            recipient=self.recipient_email,
            language=self.language,
            sender_key=self.sender_key,
            context={
                "verification_token": self.verification_token,
                "verification_url": self.verification_url,
                "email": self.recipient_email,
            },
        )


@dataclass
class PasswordResetEmailCommand:
    """Command to send password reset link."""
    
    recipient_email: str
    reset_token: str
    reset_url: str
    language: str = "en"
    sender_key: Optional[str] = None
    
    def to_send_notification_command(self) -> SendNotificationCommand:
        """Convert to generic SendNotificationCommand."""
        return SendNotificationCommand(
            template_key="password_reset",
            channel=Channel.EMAIL,
            recipient=self.recipient_email,
            language=self.language,
            sender_key=self.sender_key,
            context={
                "reset_token": self.reset_token,
                "reset_url": self.reset_url,
                "email": self.recipient_email,
            },
        )


@dataclass
class WelcomeEmailCommand:
    """Command to send welcome email to new user."""
    
    recipient_email: str
    recipient_name: Optional[str] = None
    language: str = "en"
    sender_key: Optional[str] = None
    
    def to_send_notification_command(self) -> SendNotificationCommand:
        """Convert to generic SendNotificationCommand."""
        return SendNotificationCommand(
            template_key="welcome_email",
            channel=Channel.EMAIL,
            recipient=self.recipient_email,
            language=self.language,
            sender_key=self.sender_key,
            context={
                "email": self.recipient_email,
                "name": self.recipient_name or self.recipient_email.split("@")[0],
            },
        )


@dataclass
class MagicLinkEmailCommand:
    """Command to send passwordless login link."""
    
    recipient_email: str
    magic_token: str
    magic_link_url: str
    language: str = "en"
    sender_key: Optional[str] = None
    
    def to_send_notification_command(self) -> SendNotificationCommand:
        """Convert to generic SendNotificationCommand."""
        return SendNotificationCommand(
            template_key="magic_link",
            channel=Channel.EMAIL,
            recipient=self.recipient_email,
            language=self.language,
            sender_key=self.sender_key,
            context={
                "magic_token": self.magic_token,
                "magic_link_url": self.magic_link_url,
                "email": self.recipient_email,
            },
        )


__all__ = [
    "SendNotificationCommand",
    "NotificationLogDTO",
    "NotificationSenderDTO",
    "NotificationTemplateDTO",
    "NotificationLogQuery",
    "VerificationEmailCommand",
    "PasswordResetEmailCommand",
    "WelcomeEmailCommand",
    "MagicLinkEmailCommand",
]
