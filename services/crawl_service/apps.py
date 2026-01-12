"""
Django App Configuration for Crawl Service
"""

import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CrawlServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'services.crawl_service'
    verbose_name = 'Crawl Service'
    
    def ready(self):
        """
        Import admin to register models and connect signals.
        Auto-start scheduler if enabled in config.
        """
        # Import admin to ensure models are registered
        from .admin import admin
        
        # Import signals to connect receivers
        from . import signals
        
        # Auto-start scheduler if enabled in config
        try:
            from .infrastructure.auto_recording import get_auto_record_config
            from .infrastructure.scheduler_manager import get_scheduler_manager
            
            cfg = get_auto_record_config()
            cron_cfg = cfg.get('_cron_config', {})
            
            if cron_cfg.get('scheduler_enabled', True):
                manager = get_scheduler_manager()
                if not manager.is_running():
                    success, msg = manager.start()
                    if success:
                        logger.info(f"✓ Auto-record scheduler started on app ready")
                    else:
                        logger.warning(f"✗ Failed to start scheduler: {msg}")
        except Exception as e:
            logger.error(f"Error during scheduler auto-start: {e}", exc_info=True)
