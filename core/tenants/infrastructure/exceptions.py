"""
Exception Handlers - Xử lý exception từ service layer

Convert domain exceptions → HTTP responses
"""
from rest_framework import status
from rest_framework.response import Response

from core.tenants.domain import (
    TenantNotFoundError,
    TenantAlreadyExistsError,
    InvalidTenantSlugError,
    TenantDomainInvalidError,
)


def handle_tenant_exception(exc: Exception) -> Response:
    """
    Convert domain exception → HTTP response
    
    Args:
        exc: Exception từ service/domain layer
    
    Returns:
        DRF Response object
    """
    if isinstance(exc, TenantNotFoundError):
        return Response(
            {"error": str(exc)},
            status=status.HTTP_404_NOT_FOUND,
        )
    
    if isinstance(exc, TenantAlreadyExistsError):
        return Response(
            {"error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    if isinstance(exc, (InvalidTenantSlugError, TenantDomainInvalidError)):
        return Response(
            {"error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Default: internal server error
    return Response(
        {"error": "Internal server error"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
