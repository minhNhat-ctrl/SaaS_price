"""
Products Shared Domain Layer

Pure business logic for shared data in PUBLIC schema.
No framework dependencies.

Entities:
- Domain: Website domain information
- ProductURL: Shared URL records
- PriceHistory: Price history data
"""

from .entities import (
    Domain,
    ProductURL,
    PriceHistory,
)

from .exceptions import (
    SharedDomainError,
    DomainNotFoundError,
    ProductURLNotFoundError,
    ProductURLAlreadyExistsError,
    InvalidURLError,
    OrphanedURLError,
)

# Aliases for compatibility
URLNotFoundError = ProductURLNotFoundError
DuplicateURLError = ProductURLAlreadyExistsError
DuplicateDomainError = SharedDomainError

__all__ = [
    # Entities
    'Domain',
    'ProductURL',
    'PriceHistory',
    # Exceptions
    'SharedDomainError',
    'DomainNotFoundError',
    'ProductURLNotFoundError',
    'ProductURLAlreadyExistsError',
    'InvalidURLError',
    'OrphanedURLError',
    # Aliases
    'URLNotFoundError',
    'DuplicateURLError',
    'DuplicateDomainError',
]
