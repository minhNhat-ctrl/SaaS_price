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
    name = 'core.admin_core'
    verbose_name = 'Admin Core'

    def ready(self):
        """
        Called when Django starts
        
        Thực hiện:
        1. Initialize hash service (disabled - using fixed hash in urls.py)
        2. Auto-load module admin configs
        3. Setup middleware
        """
        # Hash service disabled - using fixed hash in config/urls.py
        # No need to generate random hash anymore
        pass
        
        # TODO: Auto-load modules
        # from core.admin_core.services import AdminModuleLoader
        # loader = AdminModuleLoader()
        # await loader.discover_and_load_modules(modules_dir='core')
