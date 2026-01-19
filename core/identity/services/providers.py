"""Factory helpers for wiring Identity services."""
from __future__ import annotations

from typing import Optional

from core.identity.infrastructure.django_repository import DjangoAllauthIdentityRepository
from core.identity.repositories import IdentityRepository
from core.identity.services.identity_service import IdentityService

__all__ = [
    "get_identity_service",
]


def get_identity_service(repository: Optional[IdentityRepository] = None) -> IdentityService:
    """Return an IdentityService configured with the default repository."""
    repo = repository or DjangoAllauthIdentityRepository()
    return IdentityService(repository=repo)
