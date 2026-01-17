"""Base orchestrator abstractions for coordinating module use cases."""
from abc import ABC, abstractmethod
from typing import Any


class Orchestrator(ABC):
    """Defines the contract for orchestrators coordinating multiple use cases."""

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Run the orchestrator workflow."""
        raise NotImplementedError
