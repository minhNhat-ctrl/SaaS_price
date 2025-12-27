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
    name = 'platform.tenants'
    verbose_name = 'Tenants'

    def ready(self):
        """
        Called when Django starts
        Có thể dùng để:
        - Đăng ký signals
        - Initialize caching
        - Setup event handlers
        """
        # TODO: Import signal handlers nếu cần
        # from .infrastructure import signals
        pass
