"""
Domain Entities for Accounts Module

Pure business logic - no Django dependencies.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from uuid import UUID


class ProfileScope(Enum):
    """Profile scope - global or tenant-specific."""
    GLOBAL = "global"  # Single profile across all tenants
    TENANT = "tenant"  # Separate profile per tenant


class NotificationChannel(Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Avatar:
    """
    Avatar/profile photo entity.
    
    Supports:
    - File upload
    - External URL (Gravatar, social media)
    - Size variants (thumbnail, medium, large)
    """
    id: UUID
    user_id: UUID
    tenant_id: Optional[UUID] = None
    file_path: Optional[str] = None  # Relative path in storage
    file_url: Optional[str] = None   # Full URL for serving
    external_url: Optional[str] = None  # External avatar URL
    file_size: int = 0  # Bytes
    mime_type: str = "image/jpeg"
    width: int = 0
    height: int = 0
    uploaded_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_uploaded(self) -> bool:
        """Check if avatar is uploaded (vs external)."""
        return bool(self.file_path)
    
    def get_url(self) -> str:
        """Get avatar URL (uploaded or external)."""
        return self.file_url or self.external_url or ""


@dataclass
class NotificationSettings:
    """
    User notification preferences.
    
    Controls which notifications to receive and through which channels.
    """
    id: UUID
    user_id: UUID
    tenant_id: Optional[UUID] = None
    
    # Channel enablement
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    in_app_enabled: bool = True
    
    # Notification types
    marketing_enabled: bool = True
    product_updates_enabled: bool = True
    security_alerts_enabled: bool = True
    mentions_enabled: bool = True
    
    # Digest preferences
    daily_digest: bool = False
    weekly_digest: bool = False
    
    # Quiet hours (24-hour format)
    quiet_hours_start: Optional[str] = None  # e.g., "22:00"
    quiet_hours_end: Optional[str] = None    # e.g., "08:00"
    
    # Custom settings (JSON-like)
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_channel_enabled(self, channel: NotificationChannel) -> bool:
        """Check if notification channel is enabled."""
        channel_map = {
            NotificationChannel.EMAIL: self.email_enabled,
            NotificationChannel.SMS: self.sms_enabled,
            NotificationChannel.PUSH: self.push_enabled,
            NotificationChannel.IN_APP: self.in_app_enabled,
        }
        return channel_map.get(channel, False)
    
    def enable_channel(self, channel: NotificationChannel):
        """Enable notification channel."""
        if channel == NotificationChannel.EMAIL:
            self.email_enabled = True
        elif channel == NotificationChannel.SMS:
            self.sms_enabled = True
        elif channel == NotificationChannel.PUSH:
            self.push_enabled = True
        elif channel == NotificationChannel.IN_APP:
            self.in_app_enabled = True
        self.updated_at = datetime.utcnow()
    
    def disable_channel(self, channel: NotificationChannel):
        """Disable notification channel."""
        if channel == NotificationChannel.EMAIL:
            self.email_enabled = False
        elif channel == NotificationChannel.SMS:
            self.sms_enabled = False
        elif channel == NotificationChannel.PUSH:
            self.push_enabled = False
        elif channel == NotificationChannel.IN_APP:
            self.in_app_enabled = False
        self.updated_at = datetime.utcnow()


@dataclass
class UserPreferences:
    """
    User preferences and settings.
    
    Stores:
    - UI preferences (theme, language, timezone)
    - Display settings
    - Feature flags
    - Custom preferences
    """
    id: UUID
    user_id: UUID
    tenant_id: Optional[UUID] = None
    
    # Localization
    language: str = "en"
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    time_format: str = "24h"  # "12h" or "24h"
    
    # UI preferences
    theme: str = "light"  # "light", "dark", "auto"
    sidebar_collapsed: bool = False
    compact_mode: bool = False
    
    # Display settings
    items_per_page: int = 25
    default_view: str = "grid"  # "grid", "list", "table"
    
    # Feature preferences
    show_onboarding: bool = True
    enable_animations: bool = True
    enable_sound: bool = False
    
    # Custom preferences (JSON-like)
    custom_preferences: Dict[str, Any] = field(default_factory=dict)
    
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get custom preference value."""
        return self.custom_preferences.get(key, default)
    
    def set_preference(self, key: str, value: Any):
        """Set custom preference value."""
        self.custom_preferences[key] = value
        self.updated_at = datetime.utcnow()
    
    def remove_preference(self, key: str):
        """Remove custom preference."""
        if key in self.custom_preferences:
            del self.custom_preferences[key]
            self.updated_at = datetime.utcnow()


@dataclass
class UserProfile:
    """
    User profile entity - personal information and settings.
    
    Can be scoped:
    - Global: Single profile across all tenants
    - Tenant: Separate profile per tenant
    
    Contains:
    - Basic info (name, bio, location)
    - Contact info (phone, social links)
    - Avatar
    - Preferences
    - Notification settings
    """
    id: UUID
    user_id: UUID  # Reference to user from identity module
    scope: ProfileScope = ProfileScope.GLOBAL
    tenant_id: Optional[UUID] = None  # Required if scope=TENANT
    
    # Basic information
    display_name: str = ""
    first_name: str = ""
    last_name: str = ""
    bio: str = ""
    title: str = ""  # Job title
    company: str = ""
    location: str = ""
    
    # Contact information
    phone: str = ""
    website: str = ""
    
    # Social links
    twitter: str = ""
    linkedin: str = ""
    github: str = ""
    
    # Avatar
    avatar: Optional[Avatar] = None
    
    # Settings
    preferences: Optional[UserPreferences] = None
    notification_settings: Optional[NotificationSettings] = None
    
    # Metadata
    is_public: bool = False  # Public profile visibility
    is_verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_full_name(self) -> str:
        """Get full name (first + last)."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.display_name or self.first_name or self.last_name or ""
    
    def get_initials(self) -> str:
        """Get user initials (2 letters)."""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        name = self.display_name or self.first_name or self.last_name
        if name:
            parts = name.split()
            if len(parts) >= 2:
                return f"{parts[0][0]}{parts[1][0]}".upper()
            return name[:2].upper()
        return "U"
    
    def update_basic_info(
        self,
        display_name: str = None,
        first_name: str = None,
        last_name: str = None,
        bio: str = None,
        title: str = None,
        company: str = None,
        location: str = None,
    ):
        """Update basic profile information."""
        if display_name is not None:
            self.display_name = display_name
        if first_name is not None:
            self.first_name = first_name
        if last_name is not None:
            self.last_name = last_name
        if bio is not None:
            self.bio = bio
        if title is not None:
            self.title = title
        if company is not None:
            self.company = company
        if location is not None:
            self.location = location
        self.updated_at = datetime.utcnow()
    
    def update_contact_info(
        self,
        phone: str = None,
        website: str = None,
        twitter: str = None,
        linkedin: str = None,
        github: str = None,
    ):
        """Update contact information."""
        if phone is not None:
            self.phone = phone
        if website is not None:
            self.website = website
        if twitter is not None:
            self.twitter = twitter
        if linkedin is not None:
            self.linkedin = linkedin
        if github is not None:
            self.github = github
        self.updated_at = datetime.utcnow()
    
    def set_avatar(self, avatar: Avatar):
        """Set profile avatar."""
        self.avatar = avatar
        self.updated_at = datetime.utcnow()
    
    def is_tenant_profile(self) -> bool:
        """Check if this is a tenant-specific profile."""
        return self.scope == ProfileScope.TENANT and self.tenant_id is not None
    
    def is_global_profile(self) -> bool:
        """Check if this is a global profile."""
        return self.scope == ProfileScope.GLOBAL
