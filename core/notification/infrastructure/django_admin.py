"""Django admin registration for notification models."""
import smtplib
from email.message import EmailMessage
from typing import Optional

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm
from django.utils import timezone
from django.utils.html import format_html
from core.admin_core.infrastructure.custom_admin import default_admin_site
from .django_models import NotificationSenderModel, NotificationTemplateModel, NotificationLogModel


@admin.register(NotificationSenderModel, site=default_admin_site)
class NotificationSenderAdmin(admin.ModelAdmin):
    """Admin for notification senders."""
    
    list_display = ['sender_key', 'channel', 'provider', 'status_badge', 'from_email', 'updated_at']
    list_filter = ['channel', 'is_active', 'is_default', 'provider']
    search_fields = ['sender_key', 'from_email', 'provider']
    readonly_fields = ['id', 'created_at', 'updated_at']
    actions = ['action_test_sender']
    
    fieldsets = (
        ('Identity', {
            'fields': ('id', 'sender_key')
        }),
        ('Channel Configuration', {
            'fields': ('channel', 'provider', 'is_active', 'is_default')
        }),
        ('Endpoint', {
            'fields': ('endpoint_host', 'endpoint_port'),
            'classes': ('collapse',)
        }),
        ('Outgoing Email (SMTP)', {
            'fields': ('from_email', 'from_name', 'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password'),
            'classes': ('collapse',)
        }),
        ('Incoming Email (POP3/IMAP)', {
            'fields': ('pop3_host', 'pop3_port', 'pop3_username', 'pop3_password'),
            'classes': ('collapse',)
        }),
        ('Credentials', {
            'fields': ('credentials_json',),
            'description': 'Provider API keys and credentials (encrypted at rest)'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    class TestSenderActionForm(ActionForm):
        """Action form to capture manual test input."""

        test_recipient = forms.CharField(
            required=True,
            label='Send test to',
            help_text='Email address or endpoint to receive the test message.'
        )
        test_description = forms.CharField(
            required=False,
            label='Description',
            widget=forms.Textarea(attrs={'rows': 2}),
            help_text='Optional note included in the test message body.'
        )

    action_form = TestSenderActionForm
    
    def status_badge(self, obj):
        """Display active/inactive status."""
        color = 'green' if obj.is_active else 'red'
        status = '✓ Active' if obj.is_active else '✗ Inactive'
        return format_html(f'<span style="color: {color}; font-weight: bold;">{status}</span>')
    status_badge.short_description = 'Status'

    def action_test_sender(self, request, queryset):
        """Send a manual test message using selected sender configurations."""

        recipient = request.POST.get('test_recipient', '').strip()
        description = request.POST.get('test_description', '').strip()

        if not recipient:
            self.message_user(request, 'Test recipient is required.', level=messages.ERROR)
            return

        for sender in queryset:
            if sender.channel != 'EMAIL':
                self.message_user(
                    request,
                    f"Sender '{sender.sender_key}' uses unsupported channel '{sender.channel}' for manual test.",
                    level=messages.WARNING,
                )
                continue

            try:
                external_id = self._send_test_email(sender, recipient, description)
            except Exception as exc:  # pragma: no cover - network dependent
                self._record_test_log(sender, recipient, 'FAILED', str(exc), external_id=None)
                self.message_user(
                    request,
                    f"Test send failed for '{sender.sender_key}': {exc}",
                    level=messages.ERROR,
                )
                continue

            self._record_test_log(sender, recipient, 'SENT', '', external_id=external_id)
            self.message_user(
                request,
                f"Test message sent successfully via '{sender.sender_key}'.",
                level=messages.SUCCESS,
            )

    action_test_sender.short_description = 'Send manual test message'

    def _send_test_email(self, sender: NotificationSenderModel, recipient: str, description: str) -> str:
        """Send a simple SMTP test email using sender configuration."""

        host = sender.smtp_host or sender.endpoint_host
        port = sender.smtp_port or sender.endpoint_port or 587

        if not host:
            raise ValueError('SMTP host or endpoint host must be configured for email channel.')

        from_address = sender.from_email or sender.smtp_username
        if not from_address:
            raise ValueError('From email or SMTP username must be provided for test send.')

        subject = description or f"Notification Sender Test ({sender.sender_key})"
        body = (
            f"This is a test message triggered from the admin panel.\n\n"
            f"Sender: {sender.sender_key}\n"
            f"Provider: {sender.provider}\n"
            f"Timestamp: {timezone.now().isoformat()}"
        )

        message = EmailMessage()
        message['Subject'] = subject
        message['From'] = from_address
        message['To'] = recipient
        message.set_content(body)

        if port == 465:
            smtp_client = smtplib.SMTP_SSL(host=host, port=port, timeout=10)
        else:
            smtp_client = smtplib.SMTP(host=host, port=port, timeout=10)

        with smtp_client as client:
            client.ehlo()
            if port not in (25, 465):
                try:
                    client.starttls()
                    client.ehlo()
                except smtplib.SMTPException:
                    pass
            if sender.smtp_username and sender.smtp_password:
                client.login(sender.smtp_username, sender.smtp_password)
            client.send_message(message)

        import uuid
        return str(uuid.uuid4())

    def _record_test_log(
        self,
        sender: NotificationSenderModel,
        recipient: str,
        status: str,
        error_message: str,
        external_id: Optional[str],
    ) -> None:
        """Persist a log entry for manual test executions."""

        NotificationLogModel.objects.create(
            template_key='__admin_test__',
            channel='EMAIL',
            recipient=recipient,
            status=status,
            error_message=error_message,
            external_id=external_id,
            context_snapshot={
                'sender_key': sender.sender_key,
                'provider': sender.provider,
                'admin_test': True,
            },
            sender_key=sender.sender_key,
            sent_at=timezone.now() if status == 'SENT' else None,
        )


@admin.register(NotificationTemplateModel, site=default_admin_site)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """Admin for notification templates."""
    
    list_display = ['template_key', 'channel', 'language', 'active_badge', 'updated_at']
    list_filter = ['channel', 'language', 'is_active']
    search_fields = ['template_key', 'subject', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Identity', {
            'fields': ('id', 'template_key')
        }),
        ('Configuration', {
            'fields': ('channel', 'language', 'is_active')
        }),
        ('Content', {
            'fields': ('subject', 'body'),
            'description': 'Supports Jinja2 template syntax'
        }),
        ('Description', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def active_badge(self, obj):
        """Display active/inactive status."""
        color = 'green' if obj.is_active else 'orange'
        status = '✓' if obj.is_active else '✗'
        return format_html(f'<span style="color: {color}; font-weight: bold; font-size: 16px;">{status}</span>')
    active_badge.short_description = 'Active'


@admin.register(NotificationLogModel, site=default_admin_site)
class NotificationLogAdmin(admin.ModelAdmin):
    """Admin for notification logs (read-only audit trail)."""
    
    list_display = ['template_key', 'channel', 'recipient_short', 'status_badge', 'sent_at', 'created_at']
    list_filter = ['channel', 'status', 'created_at']
    search_fields = ['template_key', 'recipient', 'external_id']
    readonly_fields = [
        'id', 'template_key', 'channel', 'recipient', 'status', 
        'error_message', 'external_id', 'context_snapshot', 'sender_key',
        'sent_at', 'created_at'
    ]
    
    fieldsets = (
        ('Message Details', {
            'fields': ('id', 'template_key', 'channel', 'recipient')
        }),
        ('Send Status', {
            'fields': ('status', 'status_details', 'external_id', 'sent_at')
        }),
        ('Error Details', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Context', {
            'fields': ('context_snapshot', 'sender_key'),
            'classes': ('collapse',)
        }),
        ('Timeline', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Disable adding logs (they're created by system only)."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deleting logs (audit trail)."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing logs (immutable audit trail)."""
        return False
    
    def recipient_short(self, obj):
        """Show truncated recipient."""
        if len(obj.recipient) > 40:
            return f"{obj.recipient[:40]}..."
        return obj.recipient
    recipient_short.short_description = 'Recipient'
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'SENT': 'green',
            'PENDING': 'blue',
            'FAILED': 'red',
            'BOUNCED': 'orange',
            'UNSUBSCRIBED': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(f'<span style="color: {color}; font-weight: bold;">{obj.status}</span>')
    status_badge.short_description = 'Status'
    
    def status_details(self, obj):
        """Show status with additional info."""
        if obj.status == 'FAILED':
            return f"FAILED: {obj.error_message[:100]}"
        elif obj.status == 'SENT' and obj.external_id:
            return f"SENT (ID: {obj.external_id})"
        return obj.status
    status_details.short_description = 'Status Details'
