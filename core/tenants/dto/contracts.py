"""DTO contracts for Tenants module ↔ application boundary."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID

from core.tenants.domain import TenantStatus


@dataclass(slots=True)
class TenantProvisionCommand:
    """Command payload for provisioning a new tenant instance."""

    actor_id: UUID
    name: str
    slug: str
    primary_domain: str
    auto_assign_admin: bool = True


@dataclass(slots=True)
class TenantUpdateCommand:
    """Command payload for updating tenant profile attributes."""

    actor_id: UUID
    tenant_id: UUID
    name: Optional[str] = None


@dataclass(slots=True)
class TenantStatusChangeCommand:
    """Command to transition tenant lifecycle state."""

    actor_id: UUID
    tenant_id: UUID
    target_status: TenantStatus


@dataclass(slots=True)
class TenantAddDomainCommand:
    """Command for attaching an additional domain to a tenant."""

    actor_id: UUID
    tenant_id: UUID
    domain: str
    is_primary: bool = False


@dataclass(slots=True)
class TenantListQuery:
    """Query payload for listing tenants accessible by an actor."""

    actor_id: UUID
    status: Optional[TenantStatus] = None


@dataclass(slots=True)
class TenantSummary:
    """Representation of tenant data returned to application layer."""

    id: UUID
    name: str
    slug: str
    schema_name: str
    status: TenantStatus
    domains: List[str] = field(default_factory=list)
