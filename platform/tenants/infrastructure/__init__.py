"""
Infrastructure Layer - Django / ORM / HTTP

Chứa:
- Django Models (ORM)
- Django Views / API Endpoints
- Middleware
- Concrete Repository Implementation
- Django Admin Configuration (auto-load)

Chỉ layer này được phép import Django
"""
from .api_views import TenantViewSet
from .middleware import TenantMiddleware

__all__ = ["TenantViewSet", "TenantMiddleware"]

# Note: django_admin được auto-load từ apps.py ready() method
# không cần explicit import ở đây
