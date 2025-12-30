"""
Domain Exceptions for Accounts Module

Custom exceptions for user profile and preferences operations.
"""


class AccountsException(Exception):
    """Base exception for accounts module."""
    pass


class ProfileException(AccountsException):
    """Base exception for profile operations."""
    pass


class ProfileNotFoundError(ProfileException):
    """Raised when user profile is not found."""
    def __init__(self, user_id: str, tenant_id: str = None):
        self.user_id = user_id
        self.tenant_id = tenant_id
        msg = f"Profile not found for user {user_id}"
        if tenant_id:
            msg += f" in tenant {tenant_id}"
        super().__init__(msg)


class ProfileAlreadyExistsError(ProfileException):
    """Raised when profile already exists."""
    def __init__(self, user_id: str, tenant_id: str = None):
        self.user_id = user_id
        self.tenant_id = tenant_id
        msg = f"Profile already exists for user {user_id}"
        if tenant_id:
            msg += f" in tenant {tenant_id}"
        super().__init__(msg)


class InvalidAvatarError(ProfileException):
    """Raised when avatar file is invalid."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Invalid avatar: {reason}")


class PreferencesException(AccountsException):
    """Base exception for preferences operations."""
    pass


class InvalidPreferenceError(PreferencesException):
    """Raised when preference value is invalid."""
    def __init__(self, key: str, value: any, reason: str):
        self.key = key
        self.value = value
        self.reason = reason
        super().__init__(f"Invalid preference '{key}' = '{value}': {reason}")


class NotificationException(AccountsException):
    """Base exception for notification settings operations."""
    pass


class InvalidNotificationChannelError(NotificationException):
    """Raised when notification channel is invalid."""
    def __init__(self, channel: str):
        self.channel = channel
        super().__init__(f"Invalid notification channel: {channel}")
