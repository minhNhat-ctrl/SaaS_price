"""Base classes for application use cases."""
from abc import ABC, abstractmethod
from typing import Any, Dict


class ApplicationUseCase(ABC):
    """Abstract base class for application layer use cases."""

    @abstractmethod
    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute the use case and return a structured result."""
        raise NotImplementedError
