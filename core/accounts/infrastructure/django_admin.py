"""
Django Admin for Accounts Module

Rich admin interface for user profiles, preferences, and notifications.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from core.accounts.infrastructure.django_models import (
    UserProfile,
    UserPreferences,
    NotificationSettings,
    Avatar,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for User Profiles."""
    
    list_display = [
        'display_name_with_avatar',
        'user_id_short',
        'scope_badge',
        'tenant_id_short',
        'is_verified_icon',
        'is_public_icon',
        'created_at',
    ]
    list_filter = ['scope', 'is_verified', 'is_public', 'created_at']
    search_fields = ['user_id', 'display_name', 'first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['id', 'user_id', 'created_at', 'updated_at', 'avatar_preview']
    
    fieldsets = [
        ('Identification', {
            'fields': ['id', 'user_id', 'scope', 'tenant_id']
        }),
        ('Basic Information', {
            'fields': ['display_name', 'first_name', 'last_name', 'bio', 'title', 'company', 'location']
        }),
        ('Contact Information', {
            'fields': ['phone', 'website', 'twitter', 'linkedin', 'github']
        }),
        ('Avatar', {
            'fields': ['avatar', 'avatar_preview']
        }),
        ('Settings', {
            'fields': ['is_public', 'is_verified']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def display_name_with_avatar(self, obj):
        """Display name with avatar."""
        avatar_html = ''
        if obj.avatar and obj.avatar.url:
            avatar_html = f'<img src="{obj.avatar.url}" style="width: 30px; height: 30px; border-radius: 50%; vertical-align: middle; margin-right: 8px;">'
        name = obj.display_name or f"{obj.first_name} {obj.last_name}".strip() or str(obj.user_id)[:8]
        return format_html(f'{avatar_html}<strong>{name}</strong>')
    display_name_with_avatar.short_description = 'Profile'
    
    def user_id_short(self, obj):
        """Short user ID."""
        return format_html('<code>{}</code>', str(obj.user_id)[:8])
    user_id_short.short_description = 'User'
    
    def tenant_id_short(self, obj):
        """Short tenant ID."""
        if obj.tenant_id:
            return format_html('<code>{}</code>', str(obj.tenant_id)[:8])
        return '-'
    tenant_id_short.short_description = 'Tenant'
    
    def scope_badge(self, obj):
        """Scope badge."""
        color = '#2e7d32' if obj.scope == 'GLOBAL' else '#1976d2'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.scope
        )
    scope_badge.short_description = 'Scope'
    
    def is_verified_icon(self, obj):
        """Verified icon."""
        if obj.is_verified:
            return format_html('<span style="color: #1976d2; font-size: 16px;">✓</span>')
        return '-'
    is_verified_icon.short_description = 'Verified'
    
    def is_public_icon(self, obj):
        """Public icon."""
        if obj.is_public:
            return format_html('<span style="color: #2e7d32;">●</span>')
        return format_html('<span style="color: #d32f2f;">●</span>')
    is_public_icon.short_description = 'Public'
    
    def avatar_preview(self, obj):
        """Avatar preview."""
        if obj.avatar and obj.avatar.url:
            return format_html(
                '<img src="{}" style="max-width: 150px; max-height: 150px; border-radius: 8px;">',
                obj.avatar.url
            )
        return 'No avatar'
    avatar_preview.short_description = 'Avatar Preview'


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    """Admin interface for User Preferences."""
    
    list_display = [
        'user_id_short',
        'tenant_id_short',
        'theme_badge',
        'language',
        'timezone',
        'items_per_page',
        'updated_at',
    ]
    list_filter = ['theme', 'language', 'sidebar_collapsed']
    search_fields = ['user_id']
    readonly_fields = ['id', 'user_id', 'created_at', 'updated_at', 'custom_preferences_display']
    
    fieldsets = [
        ('Identification', {
            'fields': ['id', 'user_id', 'tenant_id']
        }),
        ('UI Preferences', {
            'fields': ['theme', 'language', 'timezone', 'date_format', 'time_format']
        }),
        ('Display Preferences', {
            'fields': ['items_per_page', 'sidebar_collapsed']
        }),
        ('Custom Preferences', {
            'fields': ['custom_preferences', 'custom_preferences_display'],
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def user_id_short(self, obj):
        return format_html('<code>{}</code>', str(obj.user_id)[:8])
    user_id_short.short_description = 'User'
    
    def tenant_id_short(self, obj):
        if obj.tenant_id:
            return format_html('<code>{}</code>', str(obj.tenant_id)[:8])
        return '-'
    tenant_id_short.short_description = 'Tenant'
    
    def theme_badge(self, obj):
        """Theme badge."""
        colors = {
            'LIGHT': '#ffd54f',
            'DARK': '#424242',
            'AUTO': '#9c27b0',
        }
        color = colors.get(obj.theme, '#999')
        text_color = 'black' if obj.theme == 'LIGHT' else 'white'
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, text_color, obj.theme
        )
    theme_badge.short_description = 'Theme'
    
    def custom_preferences_display(self, obj):
        """Display custom preferences as formatted JSON."""
        import json
        if obj.custom_preferences:
            formatted = json.dumps(obj.custom_preferences, indent=2)
            return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>', formatted)
        return 'No custom preferences'
    custom_preferences_display.short_description = 'Custom Preferences (Read-only)'


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    """Admin interface for Notification Settings."""
    
    list_display = [
        'user_id_short',
        'tenant_id_short',
        'channels_enabled',
        'digest_badge',
        'quiet_hours_badge',
        'updated_at',
    ]
    list_filter = [
        'email_enabled',
        'push_enabled',
        'sms_enabled',
        'digest_enabled',
        'quiet_hours_enabled',
        'digest_frequency',
    ]
    search_fields = ['user_id']
    readonly_fields = ['id', 'user_id', 'created_at', 'updated_at', 'category_preferences_display']
    
    fieldsets = [
        ('Identification', {
            'fields': ['id', 'user_id', 'tenant_id']
        }),
        ('Notification Channels', {
            'fields': [
                'email_enabled',
                'push_enabled',
                'in_app_enabled',
                'sms_enabled',
                'slack_enabled',
                'webhook_enabled',
            ]
        }),
        ('Digest Settings', {
            'fields': ['digest_enabled', 'digest_frequency']
        }),
        ('Quiet Hours', {
            'fields': ['quiet_hours_enabled', 'quiet_start', 'quiet_end']
        }),
        ('Category Preferences', {
            'fields': ['category_preferences', 'category_preferences_display'],
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def user_id_short(self, obj):
        return format_html('<code>{}</code>', str(obj.user_id)[:8])
    user_id_short.short_description = 'User'
    
    def tenant_id_short(self, obj):
        if obj.tenant_id:
            return format_html('<code>{}</code>', str(obj.tenant_id)[:8])
        return '-'
    tenant_id_short.short_description = 'Tenant'
    
    def channels_enabled(self, obj):
        """Display enabled channels."""
        channels = []
        if obj.email_enabled:
            channels.append('📧')
        if obj.push_enabled:
            channels.append('📱')
        if obj.in_app_enabled:
            channels.append('🔔')
        if obj.sms_enabled:
            channels.append('💬')
        if obj.slack_enabled:
            channels.append('💼')
        if obj.webhook_enabled:
            channels.append('🔗')
        
        return format_html(' '.join(channels) if channels else '-')
    channels_enabled.short_description = 'Channels'
    
    def digest_badge(self, obj):
        """Digest badge."""
        if obj.digest_enabled:
            return format_html(
                '<span style="background-color: #4caf50; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
                obj.digest_frequency.upper()
            )
        return format_html('<span style="color: #999;">Disabled</span>')
    digest_badge.short_description = 'Digest'
    
    def quiet_hours_badge(self, obj):
        """Quiet hours badge."""
        if obj.quiet_hours_enabled and obj.quiet_start and obj.quiet_end:
            return format_html(
                '<span style="background-color: #ff9800; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">🌙 {} - {}</span>',
                obj.quiet_start.strftime('%H:%M'),
                obj.quiet_end.strftime('%H:%M')
            )
        return '-'
    quiet_hours_badge.short_description = 'Quiet Hours'
    
    def category_preferences_display(self, obj):
        """Display category preferences as formatted JSON."""
        import json
        if obj.category_preferences:
            formatted = json.dumps(obj.category_preferences, indent=2)
            return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>', formatted)
        return 'No category preferences'
    category_preferences_display.short_description = 'Category Preferences (Read-only)'


@admin.register(Avatar)
class AvatarAdmin(admin.ModelAdmin):
    """Admin interface for Avatars."""
    
    list_display = [
        'avatar_thumbnail',
        'user_id_short',
        'tenant_id_short',
        'source_badge',
        'file_size_display',
        'is_active_icon',
        'created_at',
    ]
    list_filter = ['is_active', 'mime_type', 'created_at']
    search_fields = ['user_id']
    readonly_fields = ['id', 'user_id', 'file_size', 'mime_type', 'created_at', 'updated_at', 'avatar_large_preview']
    
    fieldsets = [
        ('Identification', {
            'fields': ['id', 'user_id', 'tenant_id']
        }),
        ('Avatar Source', {
            'fields': ['file', 'external_url']
        }),
        ('File Metadata', {
            'fields': ['file_size', 'mime_type']
        }),
        ('Preview', {
            'fields': ['avatar_large_preview']
        }),
        ('Settings', {
            'fields': ['is_active']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def avatar_thumbnail(self, obj):
        """Avatar thumbnail."""
        if obj.url:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;">',
                obj.url
            )
        return '-'
    avatar_thumbnail.short_description = 'Avatar'
    
    def user_id_short(self, obj):
        return format_html('<code>{}</code>', str(obj.user_id)[:8])
    user_id_short.short_description = 'User'
    
    def tenant_id_short(self, obj):
        if obj.tenant_id:
            return format_html('<code>{}</code>', str(obj.tenant_id)[:8])
        return '-'
    tenant_id_short.short_description = 'Tenant'
    
    def source_badge(self, obj):
        """Source badge."""
        if obj.file:
            return format_html(
                '<span style="background-color: #1976d2; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">📁 FILE</span>'
            )
        elif obj.external_url:
            return format_html(
                '<span style="background-color: #f57c00; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">🔗 URL</span>'
            )
        return '-'
    source_badge.short_description = 'Source'
    
    def file_size_display(self, obj):
        """Human-readable file size."""
        if obj.file_size > 0:
            size_kb = obj.file_size / 1024
            if size_kb > 1024:
                return f"{size_kb/1024:.1f} MB"
            return f"{size_kb:.1f} KB"
        return '-'
    file_size_display.short_description = 'Size'
    
    def is_active_icon(self, obj):
        """Active icon."""
        if obj.is_active:
            return format_html('<span style="color: #2e7d32;">●</span>')
        return format_html('<span style="color: #d32f2f;">●</span>')
    is_active_icon.short_description = 'Active'
    
    def avatar_large_preview(self, obj):
        """Large avatar preview."""
        if obj.url:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">',
                obj.url
            )
        return 'No avatar'
    avatar_large_preview.short_description = 'Avatar Preview'
