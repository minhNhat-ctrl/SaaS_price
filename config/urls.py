"""
URL configuration for Saas_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.conf import settings
import os

# Import CustomAdminSite instead of default admin
from core.admin_core.infrastructure.custom_admin import default_admin_site

# Fixed admin hash (set via environment variable or use default)
# To change: export ADMIN_HASH="your-custom-hash-here"
ADMIN_HASH = os.environ.get('ADMIN_HASH', 'secure-admin-2025')

urlpatterns = [
    # Standard admin (disabled - use hash-protected instead)
    # path('admin/', admin.site.urls),
    
    # Admin Core - protected by fixed hash URL using CustomAdminSite
    # URL: /admin/{ADMIN_HASH}/
    path(f'admin/{ADMIN_HASH}/', default_admin_site.urls, name='admin_hash'),

    # Shortcut alias for products_shared admin models (flat path)
    # Example: /products_shared/pricehistory/
    # Still uses the same CustomAdminSite (auth/permissions preserved)
    path('products_shared/', default_admin_site.urls),
    
    # API endpoints for React SPA
    # Application layer orchestration endpoints
    # New structure: api/{domain}/{action}
    # - /api/identity/signup/, /api/identity/signin/, /api/identity/recover-password/
    # - /api/provisioning/create-tenant/
    # - /api/business/create-product/
    path('api/', include('application.api.urls')),
    
    # Legacy provisioning endpoint (kept for backward compatibility)
    # Will be deprecated once frontend migrates to /api/identity/signup/
    path('api/provisioning/', include('application.interfaces.http.provisioning.urls')),
]

# Admin URL for reference (check via manage.py shell or logs)
# Admin path: /admin/{ADMIN_HASH}/
