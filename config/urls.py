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
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
import os

# Fixed admin hash (set via environment variable or use default)
# To change: export ADMIN_HASH="your-custom-hash-here"
ADMIN_HASH = os.environ.get('ADMIN_HASH', 'secure-admin-2025')

urlpatterns = [
    # Standard admin (disabled - use hash-protected instead)
    # path('admin/', admin.site.urls),
    
    # Admin Core - protected by fixed hash URL
    # URL: /admin/{ADMIN_HASH}/
    path(f'admin/{ADMIN_HASH}/', admin.site.urls, name='admin_hash'),
    
    # Include other app URLs
    # path('api/', include('core.tenants.urls')),  # TODO: Install djangorestframework first
]

# Print admin URL for reference (remove in production)
if settings.DEBUG:
    print(f"\n{'='*60}")
    print(f"[ADMIN URL] http://dj.2kvietnam.com/admin/{ADMIN_HASH}/")
    print(f"[ADMIN URL] http://localhost:8005/admin/{ADMIN_HASH}/")
    print(f"[ADMIN HASH] {ADMIN_HASH}")
    print(f"{'='*60}\n")
