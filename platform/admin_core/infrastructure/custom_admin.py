"""
Custom Admin Site - Auto-load modules, auto-register models

Custom AdminSite có thể:
1. Auto-load django_admin.py từ các modules
2. Register models automatically
3. Customize branding
4. Add custom views
5. Provide stats/dashboard
"""
from django.contrib import admin
from django.apps import apps
import importlib


class CustomAdminSite(admin.AdminSite):
    """
    Custom AdminSite cho platform
    
    Features:
    - Auto-load admin modules từ mỗi platform module
    - Register models automatically
    - Custom branding
    - Security stats (failed attempts, etc.)
    """

    site_header = "PriceSynC - Admin Dashboard"
    site_title = "Platform Admin"
    index_title = "System Administration"

    def __init__(self, name='admin'):
        super().__init__(name)
        self.module_loader = None
        self.hash_service = None

    def set_module_loader(self, loader):
        """Set AdminModuleLoader instance"""
        self.module_loader = loader

    def set_hash_service(self, service):
        """Set AdminHashService instance"""
        self.hash_service = service

    def each_context(self, request):
        """
        Add custom context cho admin template
        """
        context = super().each_context(request)
        
        # Add stats
        if self.module_loader:
            context['loaded_modules'] = len(self.module_loader.list_modules())
            context['failed_modules'] = len(self.module_loader.list_failed_modules())

        # Add security info
        if self.hash_service:
            from platform.admin_core.infrastructure.security_middleware import AdminSecurityMiddleware
            middleware = AdminSecurityMiddleware(None)
            client_ip = middleware._get_client_ip(request)
            context['admin_hash'] = self.hash_service.get_hash()
            context['failed_attempts'] = self.hash_service.get_failed_attempts_for_ip(client_ip)

        return context

    def get_urls(self):
        """Override để thêm custom URLs"""
        from django.urls import path
        
        urls = super().get_urls()
        
        # Custom views
        custom_urls = [
            path('modules/', self.admin_site_view(self.modules_view), name='admin_modules'),
            path('stats/', self.admin_site_view(self.stats_view), name='admin_stats'),
        ]
        
        return custom_urls + urls

    def modules_view(self, request):
        """View hiển thị danh sách modules"""
        from django.shortcuts import render
        
        modules = []
        failed = {}
        
        if self.module_loader:
            modules = self.module_loader.list_modules()
            failed = self.module_loader.list_failed_modules()

        context = {
            **self.each_context(request),
            'modules': modules,
            'failed_modules': failed,
        }
        return render(request, 'admin/modules.html', context)

    def stats_view(self, request):
        """View hiển thị stats"""
        from django.shortcuts import render
        
        stats = {
            'total_apps': len(apps.get_app_configs()),
            'total_models': len(apps.get_models()),
        }

        if self.module_loader:
            stats['loaded_modules'] = len(self.module_loader.list_modules())
            stats['failed_modules'] = len(self.module_loader.list_failed_modules())

        context = {
            **self.each_context(request),
            'stats': stats,
        }
        return render(request, 'admin/stats.html', context)


# Create default admin site instance
default_admin_site = CustomAdminSite()
