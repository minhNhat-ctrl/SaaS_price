"""
Domain layer exports for Accounts module.
"""
from .entities import (
    UserProfile,
    ProfileScope,
    UserPreferences,
    NotificationSettings,
    NotificationChannel,
    NotificationPriority,
    Avatar,
)

from .exceptions import (
    AccountsException,
    ProfileException,
    ProfileNotFoundError,
    ProfileAlreadyExistsError,
    InvalidAvatarError,
    PreferencesException,
    InvalidPreferenceError,
    NotificationException,
    InvalidNotificationChannelError,
)

__all__ = [
    # Entities
    "UserProfile",
    "ProfileScope",
    "UserPreferences",
    "NotificationSettings",
    "NotificationChannel",
    "NotificationPriority",
    "Avatar",
    # Exceptions
    "AccountsException",
    "ProfileException",
    "ProfileNotFoundError",
    "ProfileAlreadyExistsError",
    "InvalidAvatarError",
    "PreferencesException",
    "InvalidPreferenceError",
    "NotificationException",
    "InvalidNotificationChannelError",
]
