"""
Repository Interfaces (Shared - Public Schema)

Abstract interfaces for shared data access.
"""

from .interfaces import (
    DomainRepository,
    ProductURLRepository,
    PriceHistoryRepository,
)

__all__ = [
    'DomainRepository',
    'ProductURLRepository',
    'PriceHistoryRepository',
]
