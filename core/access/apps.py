"""Django app configuration for Access module."""
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class AccessConfig(AppConfig):
    """Configuration for the Access (Authorization/RBAC) module."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.access'
    verbose_name = 'Access Control & RBAC'

    def ready(self):
        """Initialize access module and load infrastructure components."""
        logger.info("=" * 60)
        logger.info("Access Module Ready - Authorization & RBAC Enabled")
        logger.info("=" * 60)
        logger.info("Components: Membership, Roles, Permissions, Policies")
        logger.info("Architecture: Independent from Django admin User/Group")
        logger.info("=" * 60)

        # Auto-load Django admin registration
        from .infrastructure import django_admin  # noqa: F401
