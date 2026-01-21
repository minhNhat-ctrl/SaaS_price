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
        
        Routes to appropriate adapter based on sender.provider and channel:
        - SendGridAdapter for EMAIL/sendgrid
        - TwilioAdapter for SMS/twilio
        - FirebaseAdapter for PUSH/firebase
        - WebhookAdapter for WEBHOOK
        
        Args:
            sender: Configured sender entity
            recipient: Email/phone/token/URL
            subject: Email subject or message title
            body: Email body or message content
            context: Original context for provider-specific metadata
        
        Returns:
            Provider's message ID (external reference)
        
        Raises:
            NotificationSendError: If sending fails
        """
        
        # Route based on channel + provider
        if sender.channel.value == "email":
            if sender.provider == "sendgrid":
                return self._send_via_sendgrid(sender, recipient, subject, body, context)
            elif sender.provider == "smtp":
                return self._send_via_smtp(sender, recipient, subject, body, context)
            else:
                raise NotificationSendError(f"Unknown email provider: {sender.provider}")
        
        elif sender.channel.value == "sms":
            if sender.provider == "twilio":
                return self._send_via_twilio(sender, recipient, body, context)
            else:
                raise NotificationSendError(f"Unknown SMS provider: {sender.provider}")
        
        elif sender.channel.value == "push":
            if sender.provider == "firebase":
                return self._send_via_firebase(sender, recipient, subject, body, context)
            else:
                raise NotificationSendError(f"Unknown PUSH provider: {sender.provider}")
        
        elif sender.channel.value == "webhook":
            return self._send_via_webhook(sender, recipient, subject, body, context)
        
        else:
            raise NotificationSendError(f"Unknown channel: {sender.channel.value}")
    
    # ============================================================
    # Provider Adapters (Placeholder Implementations)
    # ============================================================
    
    def _send_via_sendgrid(
        self,
        sender: NotificationSender,
        recipient: str,
        subject: str,
        body: str,
        context: dict,
    ) -> str:
        """Send via SendGrid API."""
        # TODO: Implement SendGrid adapter
        # import sendgrid
        # sg = sendgrid.SendGridAPIClient(sender.api_key)
        # message = Mail(
        #     from_email=sender.from_email,
        #     to_emails=recipient,
        #     subject=subject,
        #     html_content=body,
        # )
        # response = sg.send(message)
        # return response.headers.get('X-Message-Id')
        
        import uuid
        return str(uuid.uuid4())
    
    def _send_via_smtp(
        self,
        sender: NotificationSender,
        recipient: str,
        subject: str,
        body: str,
        context: dict,
    ) -> str:
        """Send via SMTP."""
        # TODO: Implement SMTP adapter
        # import smtplib
        # from email.mime.text import MIMEText
        # msg = MIMEText(body)
        # msg['Subject'] = subject
        # msg['From'] = sender.from_email
        # msg['To'] = recipient
        # server = smtplib.SMTP(sender.smtp_host, sender.smtp_port)
        # server.send_message(msg)
        # server.quit()
        
        import uuid
        return str(uuid.uuid4())
    
    def _send_via_twilio(
        self,
        sender: NotificationSender,
        recipient: str,
        body: str,
        context: dict,
    ) -> str:
        """Send SMS via Twilio."""
        # TODO: Implement Twilio adapter
        # from twilio.rest import Client
        # client = Client(sender.account_sid, sender.auth_token)
        # message = client.messages.create(
        #     from_=sender.phone_number,
        #     to=recipient,
        #     body=body,
        # )
        # return message.sid
        
        import uuid
        return str(uuid.uuid4())
    
    def _send_via_firebase(
        self,
        sender: NotificationSender,
        recipient: str,
        subject: str,
        body: str,
        context: dict,
    ) -> str:
        """Send push notification via Firebase."""
        # TODO: Implement Firebase adapter
        # import firebase_admin
        # from firebase_admin import messaging
        # message = messaging.Message(
        #     notification=messaging.Notification(
        #         title=subject,
        #         body=body,
        #     ),
        #     token=recipient,
        # )
        # response = messaging.send(message)
        # return response
        
        import uuid
        return str(uuid.uuid4())
    
    def _send_via_webhook(
        self,
        sender: NotificationSender,
        recipient: str,
        subject: str,
        body: str,
        context: dict,
    ) -> str:
        """Send via webhook (HTTP POST)."""
        # TODO: Implement webhook adapter
        # import requests
        # payload = {
        #     "recipient": recipient,
        #     "subject": subject,
        #     "body": body,
        #     "context": context,
        # }
        # response = requests.post(recipient, json=payload, timeout=5)
        # return response.json().get('message_id')
        
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
