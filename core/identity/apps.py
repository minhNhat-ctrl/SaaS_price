"""
AppConfig for Identity module.

Notes:
- Requires django-allauth in INSTALLED_APPS
- No tenant, no role logic
- Provides authentication/identity primitives
"""
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class IdentityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.identity'
    verbose_name = 'Identity (Authentication)'

    def ready(self):
        logger.info("Identity module ready (django-allauth provider). Ensure INSTALLED_APPS includes 'allauth', 'allauth.account', 'allauth.socialaccount'.")
