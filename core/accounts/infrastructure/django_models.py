"""
Django Models for Accounts Module

Persistence layer - Django ORM implementation.
"""
import uuid
from django.db import models
from django.core.validators import FileExtensionValidator
from django.contrib.postgres.fields import ArrayField


class UserProfile(models.Model):
    """User profile - can be global or tenant-specific."""
    
    SCOPE_CHOICES = [
        ('GLOBAL', 'Global'),
        ('TENANT', 'Tenant'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True, help_text="User ID from identity module")
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default='GLOBAL', db_index=True)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True, help_text="Tenant ID if scope=TENANT")
    
    # Basic Info
    display_name = models.CharField(max_length=100, blank=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    bio = models.TextField(blank=True)
    title = models.CharField(max_length=100, blank=True, help_text="Job title")
    company = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=100, blank=True)
    
    # Contact Info
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    twitter = models.CharField(max_length=50, blank=True)
    linkedin = models.CharField(max_length=100, blank=True)
    github = models.CharField(max_length=50, blank=True)
    
    # Avatar (optional FK to Avatar model)
    avatar = models.ForeignKey('Avatar', null=True, blank=True, on_delete=models.SET_NULL, related_name='profiles')
    
    # Metadata
    is_public = models.BooleanField(default=True, help_text="Profile visible to others")
    is_verified = models.BooleanField(default=False, help_text="Verified profile badge")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_profile'
        indexes = [
            models.Index(fields=['user_id', 'tenant_id']),
            models.Index(fields=['scope', 'tenant_id']),
        ]
        unique_together = [('user_id', 'tenant_id')]
        ordering = ['-created_at']
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.display_name or self.user_id} ({self.scope})"


class UserPreferences(models.Model):
    """User preferences and UI settings."""
    
    THEME_CHOICES = [
        ('LIGHT', 'Light'),
        ('DARK', 'Dark'),
        ('AUTO', 'Auto'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    # UI Preferences
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='LIGHT')
    language = models.CharField(max_length=10, default='en')
    timezone = models.CharField(max_length=50, default='UTC')
    date_format = models.CharField(max_length=20, default='YYYY-MM-DD')
    time_format = models.CharField(max_length=10, default='24h')
    
    # Display Preferences
    items_per_page = models.IntegerField(default=20)
    sidebar_collapsed = models.BooleanField(default=False)
    
    # Custom Preferences (JSON)
    custom_preferences = models.JSONField(default=dict, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_preferences'
        indexes = [
            models.Index(fields=['user_id', 'tenant_id']),
        ]
        unique_together = [('user_id', 'tenant_id')]
        verbose_name = 'User Preferences'
        verbose_name_plural = 'User Preferences'
    
    def __str__(self):
        return f"Preferences for {self.user_id}"


class NotificationSettings(models.Model):
    """User notification settings."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Channel Enablement
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)
    slack_enabled = models.BooleanField(default=False)
    webhook_enabled = models.BooleanField(default=False)
    
    # Frequency
    digest_enabled = models.BooleanField(default=False)
    digest_frequency = models.CharField(max_length=20, default='daily', choices=[
        ('realtime', 'Real-time'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ])
    
    # Quiet Hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_start = models.TimeField(null=True, blank=True)
    quiet_end = models.TimeField(null=True, blank=True)
    
    # Category Preferences (JSON)
    category_preferences = models.JSONField(default=dict, blank=True, help_text="Per-category notification settings")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_notification_settings'
        indexes = [
            models.Index(fields=['user_id', 'tenant_id']),
        ]
        unique_together = [('user_id', 'tenant_id')]
        verbose_name = 'Notification Settings'
        verbose_name_plural = 'Notification Settings'
    
    def __str__(self):
        return f"Notifications for {self.user_id}"


class Avatar(models.Model):
    """User avatar - file or external URL."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    # File Upload
    file = models.ImageField(
        upload_to='avatars/%Y/%m/%d/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp'])
        ],
        help_text="Upload avatar image"
    )
    file_size = models.IntegerField(default=0, help_text="File size in bytes")
    mime_type = models.CharField(max_length=50, default='image/jpeg')
    
    # External URL (alternative to file upload)
    external_url = models.URLField(blank=True, help_text="External avatar URL (e.g., Gravatar)")
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_avatar'
        indexes = [
            models.Index(fields=['user_id', 'tenant_id']),
        ]
        ordering = ['-created_at']
        verbose_name = 'Avatar'
        verbose_name_plural = 'Avatars'
    
    def __str__(self):
        return f"Avatar for {self.user_id}"
    
    @property
    def url(self):
        """Get avatar URL."""
        if self.external_url:
            return self.external_url
        elif self.file:
            return self.file.url
        return None
