"""
Django App Configuration for Crawl Service
"""

from django.apps import AppConfig


class CrawlServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'services.crawl_service'
    verbose_name = 'Crawl Service'
    
    def ready(self):
        """
        Import admin to register models and connect signals.
        """
        # Import admin to ensure models are registered
        from .admin import admin
        
        # Import signals to connect receivers
        from . import signals
