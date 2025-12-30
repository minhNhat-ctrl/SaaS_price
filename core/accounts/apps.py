"""Django app configuration for Accounts module."""
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class AccountsConfig(AppConfig):
    """Configuration for the Accounts (User Profiles & Preferences) module."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.accounts'
    verbose_name = 'User Accounts & Profiles'

    def ready(self):
        """Initialize accounts module and load infrastructure components."""
        logger.info("=" * 60)
        logger.info("Accounts Module Ready - User Profiles Enabled")
        logger.info("=" * 60)
        logger.info("Components: Profiles, Preferences, Notifications, Avatars")
        logger.info("Architecture: Tenant-aware user profiles")
        logger.info("Independent from Django admin User model")
        logger.info("=" * 60)

        # Auto-load Django admin registration
        from .infrastructure import django_admin  # noqa: F401
