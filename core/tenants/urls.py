"""
URL Configuration cho Tenant API endpoints
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from core.tenants.infrastructure.api_views import TenantViewSet

# Router để tự động generate URLs từ ViewSet
router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')

urlpatterns = [
    path('api/', include(router.urls)),
]

"""
Generated URLs:
- GET /api/tenants/ → list
- POST /api/tenants/ → create
- GET /api/tenants/{id}/ → retrieve
- PATCH /api/tenants/{id}/ → partial_update
- DELETE /api/tenants/{id}/ → destroy (nếu implement)
- POST /api/tenants/{id}/activate/ → activate
- POST /api/tenants/{id}/suspend/ → suspend
- POST /api/tenants/{id}/add-domain/ → add_domain
"""
