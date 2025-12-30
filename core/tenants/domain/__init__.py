"""
Domain Layer - Pure Business Logic (không biết Django)

Xuất các entity và exception cho các module khác sử dụng
"""
from .tenant import Tenant, TenantStatus, TenantDomainValue
from .exceptions import (
    TenantNotFoundError,
    TenantAlreadyExistsError,
    InvalidTenantSlugError,
)

__all__ = [
    "Tenant",
    "TenantStatus",
    "TenantDomainValue",
    "TenantNotFoundError",
    "TenantAlreadyExistsError",
    "InvalidTenantSlugError",
]
