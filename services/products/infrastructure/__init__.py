"""
Infrastructure Layer (Tenant)

Django ORM implementations for tenant-owned data.
Shared data infrastructure is in products_shared module.
"""

from .django_models import (
    Product,
    ProductURLMapping,
)

from .django_repository import (
    DjangoProductRepository,
    DjangoProductURLMappingRepository,
    get_tenant_schema_name,
)

__all__ = [
    # Models
    'Product',
    'ProductURLMapping',
    # Repositories
    'DjangoProductRepository',
    'DjangoProductURLMappingRepository',
    # Helpers
    'get_tenant_schema_name',
]
