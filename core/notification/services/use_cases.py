"""Notification service (application use cases)."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from ..domain.entities import NotificationSender, NotificationTemplate, NotificationLog
from ..domain.exceptions import (
    TemplateNotFoundError,
    SenderNotFoundError,
    TemplateRenderError,
    NotificationSendError,
)
from ..domain.value_objects import SendCommand, SendStatus
from ..repositories import (
    NotificationSenderRepository,
    NotificationTemplateRepository,
    NotificationLogRepository,
)
from ..dto import NotificationLogDTO, SendNotificationCommand


class NotificationService:
    """Application service for sending notifications."""
    
    def __init__(
        self,
        sender_repo: NotificationSenderRepository,
        template_repo: NotificationTemplateRepository,
        log_repo: NotificationLogRepository,
    ):
        self.sender_repo = sender_repo
        self.template_repo = template_repo
        self.log_repo = log_repo
    
    def send(self, command: SendCommand) -> NotificationLog:
        """
        Send a notification based on command.
        
        Args:
            command: SendCommand with template_key, channel, recipient, context, etc.
        
        Returns:
            NotificationLog with send result
        
        Raises:
            TemplateNotFoundError: If template not found
            SenderNotFoundError: If sender not configured
            TemplateRenderError: If template rendering fails
            NotificationSendError: If sending fails
        """
        
        # 1. Get template
        template = self.template_repo.get_or_default_language(
            template_key=command.template_key,
            channel=command.channel,
            language=command.language,
        )
        if not template:
            raise TemplateNotFoundError(
                f"Template '{command.template_key}' not found for {command.channel.value}/{command.language}"
            )
        
        # 2. Get sender
        if command.sender_key:
            sender = self.sender_repo.get_by_key(command.sender_key)
            if not sender:
                raise SenderNotFoundError(f"Sender '{command.sender_key}' not found")
        else:
            sender = self.sender_repo.get_active_by_channel(command.channel)
            if not sender:
                raise SenderNotFoundError(f"No active sender for {command.channel.value}")
        
        # 3. Create log entry (start)
        log = NotificationLog(
            id=uuid4(),
            template_key=command.template_key,
            channel=command.channel,
            recipient=command.recipient,
            status=SendStatus.PENDING,
            context=command.context or {},
            sender_key=sender.sender_key,
            created_at=datetime.now(),
        )
        
        # 4. Render template
        try:
            rendered_subject, rendered_body = template.render(command.context)
        except Exception as e:
            log.status = SendStatus.FAILED
            log.error_message = f"Template rendering failed: {str(e)}"
            self.log_repo.save(log)
            raise TemplateRenderError(f"Failed to render template: {str(e)}") from e
        
        # 5. Send via provider (delegate to adapter based on channel/provider)
        try:
            external_id = self._send_via_provider(
                sender=sender,
                recipient=command.recipient,
                subject=rendered_subject,
                body=rendered_body,
                context=command.context,
            )
            
            log.status = SendStatus.SENT
            log.external_id = external_id
            log.sent_at = datetime.now()
        except NotificationSendError as e:
            log.status = SendStatus.FAILED
            log.error_message = str(e)
        except Exception as e:
            log.status = SendStatus.FAILED
            log.error_message = f"Unexpected error: {str(e)}"
        
        # 6. Save log
        saved_log = self.log_repo.save(log)
        
        # 7. Raise if send failed
        if saved_log.status == SendStatus.FAILED:
            raise NotificationSendError(
                channel=command.channel.value,
                recipient=command.recipient,
                reason=saved_log.error_message
            )
        
        return saved_log

    def send_from_dto(self, command: SendNotificationCommand) -> NotificationLog:
        """Send a notification using a DTO command payload."""

        return self.send(command.to_domain())

    @staticmethod
    def to_log_dto(log: NotificationLog) -> NotificationLogDTO:
        """Convert a NotificationLog domain entity into a DTO projection."""

        return NotificationLogDTO.from_domain(log)
    
    def _send_via_provider(
        self,
        sender: NotificationSender,
        recipient: str,
        subject: str,
        body: str,
        context: dict,
    ) -> Optional[str]:
        """
        Send via configured provider using adapter registry.
        
        Delegates to appropriate adapter based on sender.sender_key (config-driven).
        
        Args:
            sender: Configured sender entity with sender_key
            recipient: Email/phone/token/URL
            subject: Email subject or message title
            body: Email body or message content
            context: Original context for provider-specific metadata
        
        Returns:
            Provider's message ID (external reference)
        
        Raises:
            SenderNotFoundError: If sender_key not registered
            NotificationSendError: If sending fails
        """
        from core.notification.infrastructure.adapters import get_adapter
        
        # Get adapter for this sender_key from registry
        # If not found, raises SenderNotFoundError with helpful message
        adapter = get_adapter(sender.sender_key)
        
        # Delegate send to adapter
        return adapter.send(
            sender=sender,
            recipient=recipient,
            subject=subject,
            body=body,
            channel=sender.channel,
            context=context,
        )
    
    # ============================================================
    # Convenience Methods for Common Email Types
    # ============================================================
    
    def send_verification_email(
        self,
        recipient_email: str,
        verification_token: str,
        verification_url: str,
        language: str = "en",
        sender_key: Optional[str] = None,
    ) -> NotificationLog:
        """
        Send email verification link.
        
        Convenience method that wraps send_from_dto() with verification email DTO.
        """
        from core.notification.dto.contracts import VerificationEmailCommand
        
        cmd = VerificationEmailCommand(
            recipient_email=recipient_email,
            verification_token=verification_token,
            verification_url=verification_url,
            language=language,
            sender_key=sender_key,
        )
        
        notify_cmd = cmd.to_send_notification_command()
        return self.send_from_dto(notify_cmd)
    
    def send_password_reset_email(
        self,
        recipient_email: str,
        reset_token: str,
        reset_url: str,
        language: str = "en",
        sender_key: Optional[str] = None,
    ) -> NotificationLog:
        """
        Send password reset link.
        
        Convenience method that wraps send_from_dto() with password reset email DTO.
        """
        from core.notification.dto.contracts import PasswordResetEmailCommand
        
        cmd = PasswordResetEmailCommand(
            recipient_email=recipient_email,
            reset_token=reset_token,
            reset_url=reset_url,
            language=language,
            sender_key=sender_key,
        )
        
        notify_cmd = cmd.to_send_notification_command()
        return self.send_from_dto(notify_cmd)
    
    def send_welcome_email(
        self,
        recipient_email: str,
        recipient_name: Optional[str] = None,
        language: str = "en",
        sender_key: Optional[str] = None,
    ) -> NotificationLog:
        """
        Send welcome email to new user.
        
        Convenience method that wraps send_from_dto() with welcome email DTO.
        """
        from core.notification.dto.contracts import WelcomeEmailCommand
        
        cmd = WelcomeEmailCommand(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            language=language,
            sender_key=sender_key,
        )
        
        notify_cmd = cmd.to_send_notification_command()
        return self.send_from_dto(notify_cmd)
    
    def send_magic_link_email(
        self,
        recipient_email: str,
        magic_token: str,
        magic_link_url: str,
        language: str = "en",
        sender_key: Optional[str] = None,
    ) -> NotificationLog:
        """
        Send passwordless login link (magic link).
        
        Convenience method that wraps send_from_dto() with magic link email DTO.
        """
        from core.notification.dto.contracts import MagicLinkEmailCommand
        
        cmd = MagicLinkEmailCommand(
            recipient_email=recipient_email,
            magic_token=magic_token,
            magic_link_url=magic_link_url,
            language=language,
            sender_key=sender_key,
        )
        
        notify_cmd = cmd.to_send_notification_command()
        return self.send_from_dto(notify_cmd)
