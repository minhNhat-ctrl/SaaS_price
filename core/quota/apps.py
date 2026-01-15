import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class QuotaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.quota"
    verbose_name = "Usage & Quota"

    def ready(self) -> None:
        logger.info("Initializing Quota module (usage tracking & limit enforcement)")
        try:
            from core.admin_core.infrastructure.custom_admin import default_admin_site
            from core.quota.infrastructure.admin import UsageRecordAdmin, UsageEventAdmin  # noqa

            logger.info("Quota admin models registered")
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Failed to register quota admin: %s", exc)
