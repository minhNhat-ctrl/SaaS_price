"""
Custom Admin Site - Auto-load modules, auto-register models

Custom AdminSite có thể:
1. Gọi AdminService để load modules
2. Gọi AdminService để lấy stats
3. Customize branding
4. Add custom views
5. Provide logging & monitoring

Nguyên tắc:
- Gọi AdminService (không gọi loader/hash service trực tiếp)
- AdminService điều phối tất cả logic
- Infrastructure chỉ handle presentation
"""
from django.contrib import admin
from django.apps import apps
import logging

logger = logging.getLogger(__name__)


class CustomAdminSite(admin.AdminSite):
    """
    Custom AdminSite cho platform
    
    Features:
    - Gọi AdminService để load modules
    - Gọi AdminService để lấy stats
    - Custom branding
    - Security logging
    
    Dependencies:
    - AdminService (injected by app ready)
    """

    site_header = "PriceSynC - Admin Dashboard"
    site_title = "Platform Admin"
    index_title = "System Administration"

    def __init__(self, name='admin'):
        super().__init__(name)
        # AdminService sẽ được inject ở ready()
        self.admin_service = None

    def set_admin_service(self, service):
        """Set AdminService instance (called by app ready)"""
        self.admin_service = service

    def each_context(self, request):
        """
        Add custom context cho admin template
        """
        context = super().each_context(request)
        
        if not self.admin_service:
            logger.warning("AdminService not initialized in CustomAdminSite")
            return context
        
        try:
            # Gọi AdminService (không gọi loader trực tiếp)
            import asyncio
            
            loaded_modules = asyncio.run(self.admin_service.get_loaded_modules())
            failed_modules = asyncio.run(self.admin_service.get_failed_modules())
            
            context['loaded_modules'] = len(loaded_modules)
            context['failed_modules'] = len(failed_modules)
            context['admin_url'] = self.admin_service.get_admin_url()
            
            # Security info
            client_ip = self._get_client_ip(request)
            context['failed_attempts'] = self.admin_service.get_failed_attempts_for_ip(client_ip)
            context['max_failed_attempts'] = self.admin_service.max_failed_attempts
            
        except Exception as e:
            logger.error(f"Error getting admin stats: {str(e)}")

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
        
        if self.admin_service:
            try:
                import asyncio
                modules = asyncio.run(self.admin_service.get_loaded_modules())
                failed = asyncio.run(self.admin_service.get_failed_modules())
            except Exception as e:
                logger.error(f"Error loading modules view: {str(e)}")

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

        if self.admin_service:
            try:
                import asyncio
                loaded = asyncio.run(self.admin_service.get_loaded_modules())
                failed = asyncio.run(self.admin_service.get_failed_modules())
                stats['loaded_modules'] = len(loaded)
                stats['failed_modules'] = len(failed)
            except Exception as e:
                logger.error(f"Error loading stats view: {str(e)}")

        context = {
            **self.each_context(request),
            'stats': stats,
        }
        return render(request, 'admin/stats.html', context)

    @staticmethod
    def _get_client_ip(request) -> str:
        """Extract client IP từ request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


# Create default admin site instance
default_admin_site = CustomAdminSite()
