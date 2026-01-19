"""Service layer exports for Access module."""
from .access_service import AccessService
from .providers import get_access_service

__all__ = [
    "AccessService",
    "get_access_service",
]
