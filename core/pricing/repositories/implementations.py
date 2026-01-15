from __future__ import annotations

from typing import Dict, Iterable, Optional
from uuid import UUID

from core.pricing.domain.entities import Plan
from core.pricing.repositories.interfaces import PlanRepository


class InMemoryPlanRepository(PlanRepository):
    """Simple in-memory repository useful for tests."""

    def __init__(self) -> None:
        self._storage: Dict[UUID, Plan] = {}

    def list_all(self) -> Iterable[Plan]:
        return list(self._storage.values())

    def get_by_code(self, code: str) -> Optional[Plan]:
        for plan in self._storage.values():
            if plan.code == code:
                return plan
        return None

    def get_by_id(self, plan_id: UUID) -> Optional[Plan]:
        return self._storage.get(plan_id)

    def save(self, plan: Plan) -> Plan:
        self._storage[plan.id] = plan
        return plan

    def delete(self, plan: Plan) -> None:
        self._storage.pop(plan.id, None)
