"""Django ORM models for notification module."""
import json
from django.db import models
from django.contrib.postgres.fields import JSONField
from cryptography.fernet import Fernet
import os
from uuid import uuid4


class NotificationSenderModel(models.Model):
    """Notification sender configuration (email provider, SMS gateway, etc.)."""
    
    CHANNEL_CHOICES = [
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
        ('PUSH', 'Push Notification'),
        ('WEBHOOK', 'Webhook'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    sender_key = models.CharField(max_length=100, unique=True, help_text="Unique identifier for this sender")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    provider = models.CharField(max_length=100, help_text="e.g., 'sendgrid', 'twilio', 'firebase'")
    
    # Email-specific
    from_email = models.EmailField(null=True, blank=True, help_text="From address for email")
    from_name = models.CharField(max_length=255, null=True, blank=True, help_text="From name for email")
    
    # Credentials (encrypted)
    credentials_json = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Provider credentials (API keys, tokens, etc.). Encrypted at rest."
    )
    
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text="Default sender for this channel")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_sender'
        indexes = [
            models.Index(fields=['channel', '-is_active']),
            models.Index(fields=['provider']),
            models.Index(fields=['is_default', 'channel']),
        ]
        verbose_name = 'Notification Sender'
        verbose_name_plural = 'Notification Senders'
        ordering = ['-is_default', '-is_active', 'created_at']
    
    def __str__(self):
        return f"{self.sender_key} ({self.get_channel_display()} via {self.provider})"
    
    def get_decrypted_credentials(self) -> dict:
        """Get decrypted credentials."""
        # TODO: Implement encryption/decryption with NOTIFICATION_ENCRYPTION_KEY
        return self.credentials_json
    
    def set_encrypted_credentials(self, credentials: dict):
        """Set credentials with encryption."""
        # TODO: Implement encryption/decryption
        self.credentials_json = credentials


class NotificationTemplateModel(models.Model):
    """Notification template for rendering."""
    
    CHANNEL_CHOICES = [
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
        ('PUSH', 'Push Notification'),
        ('WEBHOOK', 'Webhook'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    template_key = models.CharField(max_length=255, help_text="Unique template identifier (e.g., 'welcome_email', 'payment_receipt')")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    language = models.CharField(max_length=10, default='en', help_text="Language code (en, vi, zh, etc.)")
    
    # Content
    subject = models.CharField(
        max_length=500, 
        help_text="Email subject or notification title (supports Jinja2 template syntax)"
    )
    body = models.TextField(help_text="Email body or notification content (supports Jinja2 template syntax)")
    
    # Metadata
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, help_text="Internal notes about template")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_template'
        unique_together = [['template_key', 'channel', 'language']]
        indexes = [
            models.Index(fields=['template_key', 'channel']),
            models.Index(fields=['language', '-is_active']),
            models.Index(fields=['channel']),
        ]
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'
        ordering = ['template_key', 'language', '-updated_at']
    
    def __str__(self):
        return f"{self.template_key} ({self.get_channel_display()} / {self.language})"


class NotificationLogModel(models.Model):
    """Audit trail for notification sends."""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('BOUNCED', 'Bounced'),
        ('UNSUBSCRIBED', 'Unsubscribed'),
    ]
    
    CHANNEL_CHOICES = [
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
        ('PUSH', 'Push Notification'),
        ('WEBHOOK', 'Webhook'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    
    # What was sent
    template_key = models.CharField(max_length=255, db_index=True)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    
    # Who received it
    recipient = models.CharField(max_length=500, help_text="Email, phone number, device token, or webhook URL")
    
    # Status & tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    error_message = models.TextField(blank=True, help_text="Error details if status is FAILED")
    external_id = models.CharField(max_length=255, null=True, blank=True, help_text="Provider's message ID for tracking")
    
    # Rendering & sending context
    context_snapshot = models.JSONField(default=dict, help_text="Template variables used for rendering")
    sender_key = models.CharField(max_length=100, null=True, blank=True, help_text="Which sender sent this")
    
    # Timestamps
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'notification_log'
        indexes = [
            models.Index(fields=['template_key', 'channel', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['external_id']),
        ]
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.template_key} → {self.recipient} [{self.status}]"
