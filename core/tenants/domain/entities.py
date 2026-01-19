"""Domain entities for the Tenants module."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID, uuid4

from .exceptions import InvalidTenantSlugError, TenantDomainInvalidError
from .value_objects import TenantDomainValue


class TenantStatus(Enum):
    """Lifecycle status for a tenant instance."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


@dataclass
class Tenant:
    """Aggregate root representing a SaaS tenant."""

    id: UUID
    name: str
    slug: str
    status: TenantStatus
    schema_name: str
    domains: List[TenantDomainValue] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        self._validate_slug()
        self._ensure_primary_domain()

    def _validate_slug(self) -> None:
        pattern = r"^[a-z0-9](?:[a-z0-9-]{1,98}[a-z0-9])?$"
        if not re.match(pattern, self.slug):
            raise InvalidTenantSlugError(self.slug)

    def _ensure_primary_domain(self) -> None:
        primary_domains = [domain for domain in self.domains if domain.is_primary]
        if len(primary_domains) > 1:
            for index, domain in enumerate(self.domains):
                domain.is_primary = index == 0

    @classmethod
    def create(
        cls,
        name: str,
        slug: str,
        schema_name: str,
        domains: List[TenantDomainValue],
        status: TenantStatus = TenantStatus.ACTIVE,
    ) -> "Tenant":
        return cls(
            id=uuid4(),
            name=name.strip(),
            slug=slug.strip().lower(),
            schema_name=schema_name.strip().lower(),
            status=status,
            domains=domains,
        )

    def activate(self) -> None:
        self.status = TenantStatus.ACTIVE
        self.updated_at = datetime.utcnow()

    def suspend(self) -> None:
        self.status = TenantStatus.SUSPENDED
        self.updated_at = datetime.utcnow()

    def delete(self) -> None:
        self.status = TenantStatus.DELETED
        self.updated_at = datetime.utcnow()

    def add_domain(self, domain: TenantDomainValue) -> None:
        if any(existing.domain == domain.domain for existing in self.domains):
            raise TenantDomainInvalidError(f"Domain {domain.domain} already exists")
        if domain.is_primary:
            for existing in self.domains:
                existing.is_primary = False
        self.domains.append(domain)
        self.updated_at = datetime.utcnow()

    def is_active(self) -> bool:
        return self.status == TenantStatus.ACTIVE

    def __str__(self) -> str:  # pragma: no cover - debugging helper
        return f"Tenant(id={self.id}, name={self.name}, slug={self.slug})"
