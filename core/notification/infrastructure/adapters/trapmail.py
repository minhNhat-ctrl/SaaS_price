"""Trapmail email provider adapter - SMTP implementation."""
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional
import uuid

from core.notification.domain.entities import NotificationSender
from core.notification.domain.exceptions import NotificationSendError
from core.notification.domain.value_objects import Channel
from .base import NotificationProviderAdapter

logger = logging.getLogger(__name__)


class TrapmailAdapter(NotificationProviderAdapter):
    """
    Trapmail provider adapter for sending emails via SMTP.
    
    Uses NotificationSender fields:
    - smtp_host (or endpoint_host fallback)
    - smtp_port (or endpoint_port fallback, default 587)
    - smtp_username
    - smtp_password
    - from_email (or smtp_username fallback)
    """
    
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
        Send email via Trapmail SMTP.
        
        Raises:
            NotificationSendError: If send fails or config invalid
        """
        if channel != Channel.EMAIL:
            raise NotificationSendError(
                channel=channel.value,
                recipient=recipient,
                reason="Trapmail adapter only supports EMAIL channel"
            )
        
        logger.info(
            f"[Trapmail Adapter] Sending email to {recipient} "
            f"via {sender.sender_key} (provider={sender.provider})"
        )
        
        # Extract SMTP config from sender credentials (stored as JSON dict)
        credentials = sender.credentials or {}
        smtp_host = credentials.get('smtp_host') or sender.from_email  # Fallback: some use from_email as host
        smtp_port = credentials.get('smtp_port', 587)
        smtp_username = credentials.get('smtp_username')
        smtp_password = credentials.get('smtp_password')
        from_address = sender.from_email or smtp_username
        
        # Validate required config
        if not smtp_host:
            raise NotificationSendError(
                channel=channel.value,
                recipient=recipient,
                reason=f"SMTP host not configured for sender {sender.sender_key}"
            )
        if not from_address:
            raise NotificationSendError(
                channel=channel.value,
                recipient=recipient,
                reason=f"From email not configured for sender {sender.sender_key}"
            )
        
        logger.info(f"[Trapmail Adapter] Using SMTP: {smtp_host}:{smtp_port}, from={from_address}")
        
        # Build email message
        message = EmailMessage()
        message['Subject'] = subject
        message['From'] = from_address
        message['To'] = recipient
        
        # Set body (support HTML)
        if '<html' in body.lower() or '<body' in body.lower():
            message.add_alternative(body, subtype='html')
        else:
            message.set_content(body)
        
        # Send via SMTP
        try:
            if smtp_port == 465:
                # SSL connection
                smtp_client = smtplib.SMTP_SSL(host=smtp_host, port=smtp_port, timeout=30)
            else:
                # TLS connection (default 587)
                smtp_client = smtplib.SMTP(host=smtp_host, port=smtp_port, timeout=30)
            
            with smtp_client as client:
                client.ehlo()
                
                # Upgrade to TLS if not using SSL
                if smtp_port not in (25, 465):
                    try:
                        client.starttls()
                        client.ehlo()
                    except smtplib.SMTPException:
                        logger.warning("[Trapmail Adapter] STARTTLS not supported, continuing without TLS")
                
                # Login if credentials provided
                if smtp_username and smtp_password:
                    client.login(smtp_username, smtp_password)
                
                # Send message
                client.send_message(message)
            
            # Generate external ID (Trapmail doesn't return message ID)
            external_id = f"trapmail_{uuid.uuid4().hex[:12]}"
            logger.info(f"[Trapmail Adapter] Email sent successfully! External ID: {external_id}")
            
            return external_id
            
        except Exception as e:
            logger.error(f"[Trapmail Adapter] SMTP send failed: {e}")
            raise NotificationSendError(
                channel=channel.value,
                recipient=recipient,
                reason=f"SMTP send failed: {str(e)}"
            )
