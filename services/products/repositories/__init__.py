"""
Repository Interfaces (Tenant)

Abstract interfaces for tenant-owned data access.
"""

from .interfaces import (
    ProductRepository,
    ProductURLMappingRepository,
)

__all__ = [
    'ProductRepository',
    'ProductURLMappingRepository',
]
