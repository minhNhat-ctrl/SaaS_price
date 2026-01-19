"""Factory helpers for wiring Tenant services."""
from __future__ import annotations

from typing import Optional

from core.tenants.repositories import TenantRepository
from core.tenants.infrastructure.django_repository import DjangoTenantRepository
from core.tenants.services.tenant_service import TenantService

__all__ = [
    "get_tenant_service",
]


def get_tenant_service(repository: Optional[TenantRepository] = None) -> TenantService:
    """Return a TenantService instance with default infrastructure wiring."""
    repo = repository or DjangoTenantRepository()
    return TenantService(repository=repo)
