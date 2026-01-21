"""Adapters package exports."""
from .base import NotificationProviderAdapter
from .registry import get_adapter, register_adapter, list_registered_providers

__all__ = [
    "NotificationProviderAdapter",
    "get_adapter",
    "register_adapter",
    "list_registered_providers",
]
