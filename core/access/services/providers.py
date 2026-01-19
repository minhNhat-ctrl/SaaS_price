"""Factory helpers for Access module services."""
from core.access.services.access_service import AccessService
from core.access.infrastructure.django_repository import (
    DjangoMembershipRepository,
    DjangoRoleRepository,
    DjangoPermissionRepository,
    DjangoPolicyRepository,
)

__all__ = [
    "get_access_service",
]


def get_access_service() -> AccessService:
    """Return AccessService wired with Django repository implementations."""
    return AccessService(
        membership_repo=DjangoMembershipRepository(),
        role_repo=DjangoRoleRepository(),
        permission_repo=DjangoPermissionRepository(),
        policy_repo=DjangoPolicyRepository(),
    )
