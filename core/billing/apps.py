import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class BillingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.billing"
    verbose_name = "Billing & Payments"
    
    def ready(self) -> None:
        logger.info("Initializing Billing module (invoice & payment processing)")
        try:
            from core.billing.infrastructure import admin  # noqa: F401
            logger.info("Billing admin models registered")
        except Exception as exc:  # pragma: no cover
            logger.exception("Failed to register billing admin: %s", exc)
