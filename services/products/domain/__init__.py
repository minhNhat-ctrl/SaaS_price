"""Product Domain Layer"""
from services.products.domain.entities import (
    TenantProduct,
    SharedProduct,
    SharedProductURL,
    SharedPriceHistory,
    ProductStatus,
    MarketplaceType,
    PriceSource,
)
from services.products.domain.exceptions import (
    ProductDomainError,
    TenantProductNotFoundError,
    TenantProductAlreadyExistsError,
    InvalidProductStatusError,
    SharedProductNotFoundError,
    SharedProductAlreadyExistsError,
    DuplicateProductURLError,
    InvalidPriceError,
    PriceHistoryNotFoundError,
)

__all__ = [
    # Entities
    'TenantProduct',
    'SharedProduct',
    'SharedProductURL',
    'SharedPriceHistory',
    # Enums
    'ProductStatus',
    'MarketplaceType',
    'PriceSource',
    # Exceptions
    'ProductDomainError',
    'TenantProductNotFoundError',
    'TenantProductAlreadyExistsError',
    'InvalidProductStatusError',
    'SharedProductNotFoundError',
    'SharedProductAlreadyExistsError',
    'DuplicateProductURLError',
    'InvalidPriceError',
    'PriceHistoryNotFoundError',
]
