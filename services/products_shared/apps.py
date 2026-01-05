"""
Products Shared App Configuration

This module contains shared data that lives in PUBLIC schema:
- Domain: Website domains
- ProductURL: Shared URL records
- PriceHistory: Price history linked by url_hash
"""
import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ProductsSharedConfig(AppConfig):
    """Configuration for Products Shared module."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'services.products_shared'
    verbose_name = 'Products Shared (Public Schema)'
    
    def ready(self):
        """Called when app is ready."""
        logger.info('=' * 60)
        logger.info('Products Shared Module Ready - Public Schema Data')
        logger.info('=' * 60)
        logger.info('Components: Domain, ProductURL, PriceHistory')
        logger.info('Schema: PUBLIC (shared across all tenants)')
        logger.info('=' * 60)
        
        # Register admin
        try:
            from .infrastructure import django_admin  # noqa: F401
        except ImportError:
            pass
