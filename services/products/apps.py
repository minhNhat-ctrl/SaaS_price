"""Products Module - Product Management Service"""
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class ProductsConfig(AppConfig):
    """Configuration for Products module."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'services.products'
    verbose_name = 'Products Management'
    
    def ready(self):
        """Initialize products module and load infrastructure components."""
        logger.info("=" * 60)
        logger.info("Products Module Ready - Product Management Enabled")
        logger.info("=" * 60)
        logger.info("Components: Tenant Products, Shared Products, URLs, Price History")
        logger.info("Architecture: Multi-tenant with shared catalog")
        logger.info("Pattern: DDD with tenant/shared data separation")
        logger.info("=" * 60)
        
        # Auto-load Django admin registration
        from .infrastructure import django_admin  # noqa: F401
