from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Optional
from uuid import UUID

from core.pricing.domain.entities import Plan


class PlanRepository(ABC):
    """Repository contract for persisting Plan aggregates."""

    @abstractmethod
    def list_all(self) -> Iterable[Plan]:
        raise NotImplementedError

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[Plan]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, plan_id: UUID) -> Optional[Plan]:
        raise NotImplementedError

    @abstractmethod
    def save(self, plan: Plan) -> Plan:
        raise NotImplementedError

    @abstractmethod
    def delete(self, plan: Plan) -> None:
        raise NotImplementedError
