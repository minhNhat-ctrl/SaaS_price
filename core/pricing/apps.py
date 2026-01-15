import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class PricingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.pricing"
    verbose_name = "Pricing & Plans"

    def ready(self) -> None:
        logger.info("Initializing Pricing module (plans & limits)")
        try:
            from core.admin_core.infrastructure.custom_admin import default_admin_site
            from core.pricing.infrastructure.adapters import register_admin

            register_admin(default_admin_site)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Failed to register pricing admin: %s", exc)
