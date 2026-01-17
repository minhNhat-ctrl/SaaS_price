"""Common DTO abstractions."""
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class UseCaseResult:
    """Standardized result object returned by application use cases."""

    success: bool
    data: Dict[str, Any]
    message: str = ""
