"""Django App Configuration for the Tenants module."""
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class TenantsConfig(AppConfig):
    """Django app configuration for multi-tenant support."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.tenants'
    verbose_name = 'Tenants (Multi-tenant)'

    def ready(self):
        """Log tenant initialization and auto-load admin registration."""

        logger.info("=" * 60)
        logger.info("Tenants App Ready - Schema-per-Tenant Enabled")
        logger.info("=" * 60)
        logger.info("Multi-tenancy Model: Shared Database + Separate Schemas")
        logger.info("Migration Strategy: Per-tenant auto-migration")
        logger.info("Configuration: TenantMixin/DomainMixin with tenant_<slug> schemas")
        logger.info("Usage: migrate per tenant via manage.py migrate --tenant=<slug>")
        logger.info("=" * 60)

        # Auto-load Django admin registration without explicit imports elsewhere
        from .infrastructure import django_admin  # noqa: F401

        # TODO: Import signal handlers if needed (e.g., schema lifecycle)
    name = 'core.tenants'
