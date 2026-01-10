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
    
    # API endpoints for React SPA
    # Identity module - authentication
    path('api/identity/', include('core.identity.infrastructure.urls')),
    
    # Accounts module - profile management
    path('api/accounts/', include('core.accounts.urls')),
    
    # Tenants module - project/tenant management
    path('api/tenants/', include('core.tenants.urls')),
    
    # Access module - RBAC and membership
    path('api/access/', include('core.access.urls')),
    
    # Products module - product management and price tracking
    path('api/products/', include('services.products.api.urls')),
    
    # Products Shared module - shared product URLs and price history
    path('api/', include('services.products_shared.api.urls')),
    
    # Crawl Service - bot-controlled web crawling
    path('api/crawl/', include('services.crawl_service.api.urls')),
]

# Admin URL for reference (check via manage.py shell or logs)
# Admin path: /admin/{ADMIN_HASH}/
