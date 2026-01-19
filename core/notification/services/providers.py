"""Factory helpers for wiring Notification services."""
from __future__ import annotations

from typing import Optional

from core.notification.repositories import (
    NotificationLogRepository,
    NotificationSenderRepository,
    NotificationTemplateRepository,
)
from core.notification.repositories.implementations import (
    DjangoNotificationLogRepository,
    DjangoNotificationSenderRepository,
    DjangoNotificationTemplateRepository,
)
from core.notification.services.use_cases import NotificationService

__all__ = ["get_notification_service"]


def get_notification_service(
    sender_repo: Optional[NotificationSenderRepository] = None,
    template_repo: Optional[NotificationTemplateRepository] = None,
    log_repo: Optional[NotificationLogRepository] = None,
) -> NotificationService:
    """Provision a NotificationService with default repository wiring."""

    sender_repository = sender_repo or DjangoNotificationSenderRepository()
    template_repository = template_repo or DjangoNotificationTemplateRepository()
    log_repository = log_repo or DjangoNotificationLogRepository()
    return NotificationService(
        sender_repo=sender_repository,
        template_repo=template_repository,
        log_repo=log_repository,
    )
