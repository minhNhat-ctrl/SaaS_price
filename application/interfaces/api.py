"""HTTP interface adapters that expose application use cases to external clients.

These adapters validate requests, invoke application use cases, and format responses.
"""
from typing import Any, Dict

from ..use_cases.base import ApplicationUseCase


class ApplicationAPIView:
    """Base adapter binding HTTP requests to application use cases."""

    use_case: ApplicationUseCase

    def __init__(self, use_case: ApplicationUseCase) -> None:
        self.use_case = use_case

    def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate payload and delegate to the underlying use case."""
        return self.use_case.execute(**payload)
