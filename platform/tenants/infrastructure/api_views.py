"""
API Views - Django REST Framework Views

Chỉ layer này nhận Django HttpRequest và trả HttpResponse
Input validation, exception handling, serialization đều ở đây
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from uuid import UUID

from platform.tenants.domain import (
    TenantNotFoundError,
    TenantAlreadyExistsError,
    InvalidTenantSlugError,
)
from platform.tenants.services import TenantService

# TODO: Implement serializers
# from .serializers import TenantSerializer, CreateTenantSerializer


class TenantViewSet(viewsets.ViewSet):
    """
    API Endpoints cho Tenant
    
    Use-case:
    - POST /api/tenants/ → Tạo tenant mới
    - GET /api/tenants/{id}/ → Lấy thông tin tenant
    - PATCH /api/tenants/{id}/ → Cập nhật tenant
    - DELETE /api/tenants/{id}/ → Xóa tenant
    - GET /api/tenants/ → Danh sách tenant (admin only)
    """
    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TODO: Inject concrete TenantService implementation
        # self.service = TenantService(DjangoTenantRepository())
        self.service = None

    def list(self, request):
        """
        GET /api/tenants/ → Danh sách tất cả tenant (admin only)
        
        Query params:
        - status: Lọc theo trạng thái (active, suspended, deleted)
        """
        try:
            # TODO: Check permission (admin only)
            # status_filter = request.query_params.get('status')
            # tenants = await self.service.list_all_tenants(status=status_filter)
            # return Response(TenantSerializer(tenants, many=True).data)
            return Response({"error": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request):
        """
        POST /api/tenants/ → Tạo tenant mới (superuser only)
        
        Request body:
        {
            "name": "Company Name",
            "slug": "company-slug",
            "domain": "company.example.com"
        }
        """
        try:
            # TODO: Validate input với serializer
            # serializer = CreateTenantSerializer(data=request.data)
            # if not serializer.is_valid():
            #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            #
            # tenant = await self.service.create_tenant(
            #     name=serializer.validated_data['name'],
            #     slug=serializer.validated_data['slug'],
            #     domain=serializer.validated_data['domain'],
            # )
            #
            # return Response(TenantSerializer(tenant).data, status=status.HTTP_201_CREATED)
            return Response({"error": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)
        except TenantAlreadyExistsError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InvalidTenantSlugError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, pk=None):
        """
        GET /api/tenants/{id}/ → Lấy thông tin tenant
        """
        try:
            # TODO: tenant = await self.service.get_tenant_by_id(UUID(pk))
            # return Response(TenantSerializer(tenant).data)
            return Response({"error": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)
        except TenantNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def partial_update(self, request, pk=None):
        """
        PATCH /api/tenants/{id}/ → Cập nhật thông tin tenant
        
        Request body:
        {
            "name": "New Name"
        }
        """
        try:
            # TODO: tenant = await self.service.update_tenant_info(
            #     tenant_id=UUID(pk),
            #     name=request.data.get('name'),
            # )
            # return Response(TenantSerializer(tenant).data)
            return Response({"error": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)
        except TenantNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        POST /api/tenants/{id}/activate/ → Activate tenant
        """
        try:
            # TODO: tenant = await self.service.activate_tenant(UUID(pk))
            # return Response(TenantSerializer(tenant).data)
            return Response({"error": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)
        except TenantNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """
        POST /api/tenants/{id}/suspend/ → Suspend tenant
        """
        try:
            # TODO: tenant = await self.service.suspend_tenant(UUID(pk))
            # return Response(TenantSerializer(tenant).data)
            return Response({"error": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)
        except TenantNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=['post'])
    def add_domain(self, request, pk=None):
        """
        POST /api/tenants/{id}/add-domain/ → Thêm domain mới
        
        Request body:
        {
            "domain": "newdomain.example.com",
            "is_primary": false
        }
        """
        try:
            # TODO: tenant = await self.service.add_domain_to_tenant(
            #     tenant_id=UUID(pk),
            #     domain=request.data.get('domain'),
            #     is_primary=request.data.get('is_primary', False),
            # )
            # return Response(TenantSerializer(tenant).data)
            return Response({"error": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)
        except TenantNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
