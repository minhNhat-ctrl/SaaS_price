"""
Services Layer - Business Logic / Use-case Implementation

Chứa logic nghiệp vụ, điều phối repository và domain logic
Không import Django, request, response
Chỉ nhận input thuần (tenant data, business objects)
"""
from .tenant_service import TenantService

__all__ = ["TenantService"]
