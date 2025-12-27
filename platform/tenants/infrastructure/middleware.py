"""
Tenant Middleware - Resolve tenant từ HTTP request

Mục đích:
- Extract domain từ HTTP request (HTTP_HOST header)
- Resolve tenant từ domain
- Attach tenant vào request object
- Để các endpoint phía sau có thể truy cập request.tenant

Luồng:
1. HTTP Request đến
2. TenantMiddleware extract domain từ HTTP_HOST
3. Query database để lấy tenant matching domain
4. request.tenant = tenant
5. Request tiếp tục tới view
"""
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
import asyncio

from platform.tenants.domain import TenantNotFoundError
from platform.tenants.services import TenantService


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware để resolve tenant từ domain
    
    Yêu cầu:
    - TenantService phải được inject vào (dependency injection)
    - Domain phải tương ứng với tenant nào đó trong database
    
    Nếu domain không tìm thấy → return 404 JSON
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # TODO: Inject TenantService
        # self.tenant_service = TenantService(DjangoTenantRepository())
        self.tenant_service = None
        super().__init__(get_response)

    def __call__(self, request):
        """
        Process request trước khi tới view
        """
        # Extract domain từ HTTP_HOST
        domain = request.META.get('HTTP_HOST', '').split(':')[0]  # Bỏ port nếu có

        if not domain:
            return JsonResponse(
                {"error": "Host header missing"},
                status=400,
            )

        # TODO: Resolve tenant từ domain
        # try:
        #     tenant = await self.tenant_service.get_tenant_by_domain(domain)
        #     request.tenant = tenant
        # except TenantNotFoundError:
        #     return JsonResponse(
        #         {"error": f"Tenant not found for domain: {domain}"},
        #         status=404,
        #     )

        # Temporarily set to None (TODO: implement)
        request.tenant = None

        response = self.get_response(request)
        return response

    @staticmethod
    def get_tenant(request) -> 'Tenant':
        """
        Helper method để lấy tenant từ request object
        
        Usage:
            tenant = TenantMiddleware.get_tenant(request)
        """
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            raise TenantNotFoundError()
        return tenant
