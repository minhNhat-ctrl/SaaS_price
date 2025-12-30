"""
Django App Configuration cho Tenants module
"""
from django.apps import AppConfig


class TenantsConfig(AppConfig):
    """
    Configuration class cho tenants app
    
    Ghi chú:
    - default_auto_field = 'django.db.models.BigAutoField'
    - Không khuyến khích dùng Django signals (thay vào đó dùng domain events)
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.tenants'
    verbose_name = 'Tenants'

    def ready(self):
        """
        Called when Django starts
        
        Auto-load admin registration:
        - Không cần import explicit trong main config
        - Module sẽ tự động đăng ký ModelAdmin khi app ready
        
        Có thể dùng để:
        - Đăng ký signals
        - Initialize caching
        - Setup event handlers
        """
        # Auto-load Django admin registration
        # This will auto-register TenantAdmin, TenantDomainAdmin
        # without needing explicit imports in main admin config
        from .infrastructure import django_admin  # noqa: F401
        
        # TODO: Import signal handlers nếu cần
        # from .infrastructure import signals
        pass
        