"""
Django App Configuration cho admin_core module

Mục đích:
- Khởi tạo AdminService (dependency injection)
- Inject AdminService vào middleware
- Inject AdminService vào admin site
- Setup logging

Workflow:
1. Django app ready
2. Initialize AdminHashService
3. Initialize AdminModuleLoader
4. Initialize AdminService (with dependencies)
5. Inject vào middleware & admin site
6. (Optional) Discover & load admin modules từ các modules khác
"""
import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AdminCoreConfig(AppConfig):
    """
    Configuration class cho admin_core app
    
    Trách nhiệm:
    - Khởi tạo services
    - Dependency injection
    - Setup middleware
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.admin_core'
    verbose_name = 'Admin Core'

    def ready(self):
        """
        Called when Django starts
        
        Thực hiện:
        1. Initialize AdminHashService
        2. Initialize AdminModuleLoader
        3. Initialize AdminService (with dependencies)
        4. Inject vào middleware & admin site
        5. (Optional) Auto-load modules
        """
        from django.conf import settings
        from core.admin_core.services import (
            AdminHashService,
            AdminModuleLoader,
            AdminService,
        )
        from core.admin_core.infrastructure.security_middleware import AdminSecurityMiddleware
        from core.admin_core.infrastructure.custom_admin import default_admin_site
        import os
        
        # 1. Initialize AdminHashService
        try:
            hash_service = AdminHashService(
                secret_key=getattr(settings, 'SECRET_KEY', None)
            )
            
            # Set admin hash from environment or use default
            admin_hash = os.environ.get('ADMIN_HASH', 'secure-admin-2025')
            hash_service.admin_hash = admin_hash
            
            logger.info("✓ AdminHashService initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize AdminHashService: {str(e)}")
            return

        # 2. Initialize AdminModuleLoader
        try:
            module_loader = AdminModuleLoader()
            logger.info("✓ AdminModuleLoader initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize AdminModuleLoader: {str(e)}")
            return

        # 3. Initialize AdminService (with dependencies)
        try:
            admin_service = AdminService(
                hash_service=hash_service,
                module_loader=module_loader,
            )
            logger.info("✓ AdminService initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize AdminService: {str(e)}")
            return

        # 4. Inject vào middleware
        try:
            # Get middleware instance nếu đã tạo
            # (không thể get middleware instance ở đây, sẽ set khi middleware init)
            # Thay vào đó, sẽ set ở AdminSecurityMiddleware.set_admin_service()
            logger.info("✓ AdminService ready for middleware injection")
        except Exception as e:
            logger.warning(f"Note: {str(e)}")

        # 5. Inject vào admin site
        try:
            default_admin_site.set_admin_service(admin_service)
            logger.info("✓ AdminService injected into CustomAdminSite")
        except Exception as e:
            logger.error(f"✗ Failed to inject AdminService into admin site: {str(e)}")

        # 6. (Optional) Auto-load admin modules
        enable_auto_load = getattr(settings, 'ADMIN_CORE_AUTO_LOAD_MODULES', True)
        if enable_auto_load:
            try:
                import asyncio
                modules = asyncio.run(
                    admin_service.discover_and_load_admin_modules(
                        modules_dir='core'
                    )
                )
                logger.info(f"✓ Loaded {len(modules)} admin modules")
                for mod in modules:
                    logger.info(f"  - {mod.name}: {', '.join(mod.models)}")
            except Exception as e:
                logger.warning(f"Note: Auto-load modules: {str(e)}")

        # Store AdminService ở settings để middleware có thể access
        settings.ADMIN_SERVICE = admin_service
        settings.ADMIN_HASH_SERVICE = hash_service
