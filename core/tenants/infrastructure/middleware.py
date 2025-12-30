"""
Tenant Middleware - Resolve tenant từ HTTP request

Mục đích:
- Extract domain từ HTTP request (HTTP_HOST header)
- Resolve tenant từ domain bằng Django-Tenants
- Set schema context trên connection
- Attach tenant vào request object

Luồng:
1. HTTP Request đến (domain: tenant.example.com)
2. TenantMiddleware extract domain từ HTTP_HOST
3. Query database để lấy Domain → Tenant
4. Set connection schema_name (Django-Tenants)
5. request.tenant = tenant
6. ORM queries tự động dùng tenant schema
7. Response trả về

Django-Tenants integration:
- Middleware này chạy SAU TenantMiddleware của django-tenants
- Django-tenants đã handle schema switching
- Task của middleware này: attach tenant entity vào request
"""
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
import logging

from core.tenants.domain import TenantNotFoundError
from core.tenants.services import TenantService
from core.tenants.repositories import TenantRepository
from core.tenants.infrastructure.django_repository import DjangoTenantRepository

logger = logging.getLogger(__name__)


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware để resolve tenant từ domain
    
    Integration với Django-Tenants:
    1. Django-tenants middleware set connection schema
    2. Middleware này attach domain entity vào request
    
    Yêu cầu:
    - TenantService có hẵn được initialized
    - Database phải có Domain record
    
    Nếu domain không tìm thấy → return 404 JSON
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Khởi tạo dependencies
        self.repository = DjangoTenantRepository()
        self.tenant_service = TenantService(self.repository)
        super().__init__(get_response)

    def __call__(self, request):
        """
        Process request trước khi tới view
        
        Notes:
        - Django-tenants middleware đã set schema context
        - Middleware này resolve domain entity
        """
        # Extract domain từ HTTP_HOST
        domain = request.META.get('HTTP_HOST', '').split(':')[0]  # Bỏ port nếu có

        if not domain:
            return JsonResponse(
                {"error": "Host header missing"},
                status=400,
            )

        # Resolve tenant từ domain (async)
        import asyncio
        try:
            tenant = asyncio.run(
                self.tenant_service.get_tenant_by_domain(domain)
            )
            request.tenant = tenant
            logger.info(f"Tenant resolved: {tenant.name} (domain: {domain})")
        except TenantNotFoundError:
            logger.warning(f"Tenant not found for domain: {domain}")
            return JsonResponse(
                {"error": f"Tenant not found for domain: {domain}"},
                status=404,
            )
        except Exception as e:
            logger.error(f"Error resolving tenant: {str(e)}")
            return JsonResponse(
                {"error": "Internal server error"},
                status=500,
            )

        response = self.get_response(request)
        return response

    @staticmethod
    def get_tenant(request) -> 'Tenant':
        """
        Helper method để lấy tenant từ request object
        
        Usage:
            tenant = TenantMiddleware.get_tenant(request)
        
        Raises:
            TenantNotFoundError: Nếu tenant không tìm thấy
        """
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            raise TenantNotFoundError()
        return tenant
