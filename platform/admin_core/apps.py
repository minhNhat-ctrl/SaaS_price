"""
Django App Configuration cho admin_core module
"""
from django.apps import AppConfig


class AdminCoreConfig(AppConfig):
    """
    Configuration class cho admin_core app
    
    Mục đích:
    - Central admin management cho platform
    - Auto-load django_admin.py từ các modules
    - Validate & register ModelAdmin
    
    Workflow:
    1. Django app ready
    2. Initialize AdminModuleLoader
    3. Scan platform/ directory
    4. Load django_admin.py từ mỗi module
    5. Auto-register with Django Admin
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'platform.admin_core'
    verbose_name = 'Admin Core'

    def ready(self):
        """
        Called when Django starts
        
        Thực hiện:
        1. Initialize hash service
        2. Auto-load module admin configs
        3. Setup middleware
        """
        from django.conf import settings
        from platform.admin_core.services import AdminHashService, AdminModuleLoader
        from platform.admin_core.infrastructure import CustomAdminSite
        
        # Create & configure hash service
        hash_service = AdminHashService(secret_key=settings.SECRET_KEY)
        hash_service.generate_hash()
        
        # Store ở settings để middleware có thể access
        settings.ADMIN_HASH_SERVICE = hash_service
        
        # Log admin URL
        admin_url = hash_service.get_admin_url()
        print(f"\n[ADMIN CORE] Admin URL: {admin_url}\n")
        
        # TODO: Auto-load modules
        # loader = AdminModuleLoader()
        # await loader.discover_and_load_modules(modules_dir='platform')
