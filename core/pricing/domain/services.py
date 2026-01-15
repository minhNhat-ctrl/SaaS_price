from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .entities import Plan
from .exceptions import PlanNotFoundError


@dataclass
class PlanCatalog:
    """In-memory catalog for plan lookup operations."""

    plans: Iterable[Plan]

    def list_active(self) -> List[Plan]:
        return [plan for plan in self.plans if plan.is_active]

    def get_by_code(self, code: str) -> Plan:
        for plan in self.plans:
            if plan.code == code:
                return plan
        raise PlanNotFoundError(f"Plan with code '{code}' not found")
