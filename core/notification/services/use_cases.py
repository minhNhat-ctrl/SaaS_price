"""Notification service (application use cases)."""
from datetime import datetime
from typing import Optional

from ..domain.entities import NotificationSender, NotificationTemplate, NotificationLog
from ..domain.exceptions import (
    TemplateNotFoundError,
    SenderNotFoundError,
    TemplateRenderError,
    NotificationSendError,
)
from ..domain.value_objects import SendCommand, SendStatus
from ..repositories.interfaces import (
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
            template_key=command.template_key,
            channel=command.channel,
            recipient=command.recipient,
            status=SendStatus.PENDING,
            context=command.context,
            sender_key=sender.sender_key,
        )
        
        # 4. Render template
        try:
            rendered_subject = template.render({'subject': template.subject}, command.context)
            rendered_body = template.render({'body': template.body}, command.context)
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
                f"Failed to send {command.channel.value} to {command.recipient}: {saved_log.error_message}"
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
        Send via configured provider.
        
        This is a placeholder - actual implementation would delegate to:
        - SendGridAdapter for EMAIL/sendgrid
        - TwilioAdapter for SMS/twilio
        - FirebaseAdapter for PUSH/firebase
        - WebhookAdapter for WEBHOOK
        
        Args:
            sender: Configured sender
            recipient: Email/phone/token/URL
            subject: Email subject or message title
            body: Email body or message content
            context: Original context for provider-specific metadata
        
        Returns:
            Provider's message ID or None
        
        Raises:
            NotificationSendError: If sending fails
        """
        
        # TODO: Implement provider adapters
        # For now, simulate success
        import uuid
        return str(uuid.uuid4())
    
    def get_sender(self, sender_key: str) -> Optional[NotificationSender]:
        """Get sender by key."""
        return self.sender_repo.get_by_key(sender_key)
    
    def get_template(self, template_key: str, channel, language: str = 'en') -> Optional[NotificationTemplate]:
        """Get template by key, channel, language."""
        return self.template_repo.get_or_default_language(template_key, channel, language)
    
    def get_send_log(self, template_key: str, limit: int = 50):
        """Get recent send logs for template."""

        return self.log_repo.list_by_template_key(template_key, limit)
