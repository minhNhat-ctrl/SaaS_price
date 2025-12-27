"""
URL Configuration cho Admin Core

Routes:
- /admin/{hash}/: Main admin interface (protected by hash)
- /admin/{hash}/modules/: View loaded modules
- /admin/{hash}/stats/: View system stats
"""
from django.urls import path, re_path
from django.contrib import admin

urlpatterns = [
    # Protected admin interface
    # Pattern: /admin/{hash}/
    # Middleware sẽ validate hash
    re_path(
        r'^admin/(?P<hash>[a-f0-9]+)/',
        admin.site.urls,
        name='admin_hash',
    ),
]

"""
Alternative: Custom admin site

from platform.admin_core.infrastructure.custom_admin import default_admin_site

urlpatterns = [
    re_path(
        r'^admin/(?P<hash>[a-f0-9]+)/',
        default_admin_site.urls,
        name='admin_hash',
    ),
]
"""
