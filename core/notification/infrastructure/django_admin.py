"""Django admin registration for notification models."""
from django.contrib import admin
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
    
    fieldsets = (
        ('Identity', {
            'fields': ('id', 'sender_key')
        }),
        ('Channel Configuration', {
            'fields': ('channel', 'provider', 'is_active', 'is_default')
        }),
        ('Email Settings', {
            'fields': ('from_email', 'from_name'),
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
    
    def status_badge(self, obj):
        """Display active/inactive status."""
        color = 'green' if obj.is_active else 'red'
        status = '✓ Active' if obj.is_active else '✗ Inactive'
        return format_html(f'<span style="color: {color}; font-weight: bold;">{status}</span>')
    status_badge.short_description = 'Status'


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
