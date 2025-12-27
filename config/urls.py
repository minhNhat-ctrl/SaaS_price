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
from platform.admin_core.services import AdminHashService

# Initialize admin hash service
admin_hash_service = AdminHashService()
admin_url_hash = admin_hash_service.generate_hash()

urlpatterns = [
    # Standard admin (disabled - use hash-protected instead)
    # path('admin/', admin.site.urls),
    
    # Admin Core - protected by hash URL
    # Example URL: /admin/{hash}/
    path(f'admin/{admin_url_hash}/', admin.site.urls, name='admin_hash'),
    
    # Include other app URLs
    path('api/', include('platform.tenants.urls')),
]

# Print admin URL for reference (remove in production)
print(f"\n{'='*60}")
print(f"[ADMIN URL] http://localhost:8000/admin/{admin_url_hash}/")
print(f"{'='*60}\n")
