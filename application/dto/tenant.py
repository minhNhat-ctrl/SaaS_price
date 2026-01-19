"""Tenant provisioning domain DTOs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CreateTenantCommand:
    """Command to create a new tenant."""
    user_id: str
    slug: Optional[str] = None
    name: Optional[str] = None


@dataclass(frozen=True)
class CreateTenantResult:
    """Result of tenant creation."""
    tenant_id: str
    status: str


@dataclass(frozen=True)
class ResolveSubscriptionResult:
    """Result of subscription resolution."""
    status: str
    trial_days: Optional[int] = None


@dataclass(frozen=True)
class AssignPlanResult:
    """Result of plan assignment."""
    plan_code: str
    requires_payment: bool


@dataclass(frozen=True)
class ActivateTenantResult:
    """Result of tenant activation."""
    status: str
