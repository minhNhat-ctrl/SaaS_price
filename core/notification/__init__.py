"""Notification module - manages all notification sending logic."""
from django.apps import AppConfig


class NotificationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.notification'
    verbose_name = 'Notification Management'
    
    def ready(self):
        """Initialize app."""
        # Register admin models
        from .infrastructure import django_admin  # noqa


default_app_config = 'core.notification.apps.NotificationConfig'
