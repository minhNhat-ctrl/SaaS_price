"""
Services Layer - Business Logic / Use-case Implementation

Chứa logic nghiệp vụ, điều phối repository và domain logic
Không import Django, request, response
Chỉ nhận input thuần (tenant data, business objects)
"""
from .tenant_service import TenantService
from .providers import get_tenant_service

__all__ = [
	"TenantService",
	"get_tenant_service",
]
