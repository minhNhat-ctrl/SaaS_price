"""Factory helpers for wiring AccountsService dependencies."""
from core.accounts.services.accounts_service import AccountsService
from core.accounts.infrastructure.django_repository import (
    DjangoProfileRepository,
    DjangoPreferencesRepository,
    DjangoNotificationSettingsRepository,
    DjangoAvatarRepository,
)

__all__ = [
    "get_accounts_service",
]


def get_accounts_service() -> AccountsService:
    """Build AccountsService with default repository implementations."""
    return AccountsService(
        profile_repo=DjangoProfileRepository(),
        preferences_repo=DjangoPreferencesRepository(),
        notification_repo=DjangoNotificationSettingsRepository(),
        avatar_repo=DjangoAvatarRepository(),
    )
