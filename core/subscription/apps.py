import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class SubscriptionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.subscription"
    verbose_name = "Subscriptions & Billing"

    def ready(self) -> None:
        logger.info("Initializing Subscription module (tenant ↔ plan binding)")
        try:
            from core.admin_core.infrastructure.custom_admin import default_admin_site
            from core.subscription.infrastructure.adapters import register_admin

            register_admin(default_admin_site)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Failed to register subscription admin: %s", exc)
