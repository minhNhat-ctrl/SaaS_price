"""
Admin Core Services - Business Logic Layer

Exported services (không import Django):
- AdminHashService: Quản lý hash URL (generation & comparison)
- AdminModuleLoader: Auto-load admin modules từ các modules
- AdminService: Điều phối logic (validate hash, load modules, rate limiting)

Nguyên tắc:
- Không import Django
- Không import request/response
- Return domain objects
"""

from .admin_hash_service import AdminHashService
from .admin_module_loader import AdminModuleLoader
from .admin_service import AdminService

__all__ = [
    'AdminHashService',
    'AdminModuleLoader',
    'AdminService',
]
