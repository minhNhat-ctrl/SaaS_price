"""Factory helpers for wiring Pricing services."""
from __future__ import annotations

from typing import Optional

from core.pricing.infrastructure.adapters import DjangoORMPlanRepository
from core.pricing.repositories.interfaces import PlanRepository
from core.pricing.services.use_cases import PlanCatalogService

__all__ = ["get_plan_catalog_service"]


def get_plan_catalog_service(repository: Optional[PlanRepository] = None) -> PlanCatalogService:
    """Provision a PlanCatalogService configured with default repository wiring."""
    repo = repository or DjangoORMPlanRepository()
    return PlanCatalogService(repository=repo)
