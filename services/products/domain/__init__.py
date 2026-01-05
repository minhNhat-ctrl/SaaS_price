"""
Product Domain Layer (Tenant)

Pure business logic for tenant-owned data.
No framework dependencies.

Entities:
- Product: Core product entity owned by tenant
- ProductURLMapping: Links a product to a shared URL via hash

Exceptions:
- ProductDomainError: Base exception
- ProductNotFoundError: Product not found
- DuplicateSKUError: SKU already exists for tenant
- DuplicateGTINError: GTIN already exists for tenant
- URLMappingNotFoundError: URL mapping not found
- DuplicateURLError: URL already exists for tenant
- InvalidURLError: Invalid URL format
"""

from .entities import (
    Product,
    ProductURLMapping,
    ProductStatus,
)

from .exceptions import (
    ProductDomainError,
    ProductNotFoundError,
    DuplicateSKUError,
    DuplicateGTINError,
    InvalidProductStatusError,
    URLMappingNotFoundError,
    DuplicateURLError,
    InvalidURLError,
)

__all__ = [
    # Entities
    'Product',
    'ProductURLMapping',
    'ProductStatus',
    # Exceptions
    'ProductDomainError',
    'ProductNotFoundError',
    'DuplicateSKUError',
    'DuplicateGTINError',
    'InvalidProductStatusError',
    'URLMappingNotFoundError',
    'DuplicateURLError',
    'InvalidURLError',
]
