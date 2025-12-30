"""
Admin Module Loader Service

Tự động scan và load django_admin.py từ các modules
Không cần config explicit - plug-and-play
"""
import os
import importlib
import sys
from typing import List, Dict, Optional
from pathlib import Path

from core.admin_core.domain import AdminModule, AdminModuleLoadError


class AdminModuleLoader:
    """
    Service để auto-load django_admin.py từ các modules
    
    Cơ chế:
    1. Scan thư mục platform/
    2. Kiểm tra mỗi module có infrastructure/django_admin.py không
    3. Import module đó
    4. Theo dõi modules đã load
    
    Lợi ích:
    - Module mới tự động có admin interface
    - Không cần chỉnh sửa admin core
    - Tuân thủ kiến trúc plug-in
    """

    def __init__(self):
        self.loaded_modules: Dict[str, AdminModule] = {}
        self.failed_modules: Dict[str, str] = {}

    async def discover_and_load_modules(
        self,
        base_path: str = None,
        modules_dir: str = "platform",
    ) -> List[AdminModule]:
        """
        Auto-discover và load tất cả admin modules
        
        Args:
            base_path: Base path của project (nếu không, dùng current directory)
            modules_dir: Tên thư mục chứa modules (default: 'platform')
        
        Returns:
            Danh sách AdminModule đã load thành công
        
        Raises:
            AdminModuleLoadError: Nếu có lỗi load critical modules
        """
        if not base_path:
            base_path = Path.cwd()
        
        modules_path = Path(base_path) / modules_dir
        
        if not modules_path.exists():
            raise AdminModuleLoadError(
                modules_dir,
                f"Directory not found: {modules_path}"
            )

        loaded = []
        
        # Scan tất cả thư mục con trong modules_path
        for module_dir in sorted(modules_path.iterdir()):
            if not module_dir.is_dir() or module_dir.name.startswith('_'):
                continue
            
            # Kiểm tra xem có django_admin.py không
            admin_file = module_dir / "infrastructure" / "django_admin.py"
            
            if not admin_file.exists():
                # Module này không có admin interface
                continue
            
            try:
                # Import module
                module_name = f"{modules_dir}.{module_dir.name}"
                admin_module_path = f"{modules_dir}.{module_dir.name}.infrastructure.django_admin"
                
                await self._load_module(
                    module_name=module_name,
                    admin_module_path=admin_module_path,
                )
                
                loaded.append(self.loaded_modules[module_name])
            
            except Exception as e:
                self.failed_modules[module_dir.name] = str(e)
                # Continue loading other modules
                continue
        
        return list(self.loaded_modules.values())

    async def _load_module(
        self,
        module_name: str,
        admin_module_path: str,
    ):
        """
        Load một module admin
        
        Args:
            module_name: Tên module (ví dụ: 'core.tenants')
            admin_module_path: Đường dẫn tới django_admin.py
        
        Raises:
            AdminModuleLoadError: Nếu import thất bại
        """
        try:
            # Import django_admin module
            admin_module = importlib.import_module(admin_module_path)
            
            # Extract app label từ module name
            app_label = module_name.split('.')[-1]
            
            # Tạo AdminModule entity
            admin_mod = AdminModule(
                name=module_name,
                app_label=app_label,
                verbose_name=app_label.replace('_', ' ').title(),
                description=f"Admin interface for {module_name}",
                admin_module_path=admin_module_path,
            )
            
            # Extract models từ admin module
            # Tìm tất cả classes kết thúc bằng "Admin"
            admin_classes = [
                name for name in dir(admin_module)
                if not name.startswith('_') and name.endswith('Admin')
            ]
            
            for admin_class_name in admin_classes:
                admin_class = getattr(admin_module, admin_class_name)
                # Extract model name từ admin class name
                # ví dụ: TenantAdmin → Tenant
                if hasattr(admin_class, 'model'):
                    model_name = admin_class.model.__name__
                else:
                    # Fallback: extract từ class name
                    model_name = admin_class_name.replace('Admin', '')
                
                admin_mod.add_model(model_name)
            
            admin_mod.mark_loaded()
            self.loaded_modules[module_name] = admin_mod
        
        except Exception as e:
            raise AdminModuleLoadError(
                module_name,
                str(e)
            )

    def get_module(self, module_name: str) -> Optional[AdminModule]:
        """Lấy module đã load"""
        return self.loaded_modules.get(module_name)

    def list_modules(self) -> List[AdminModule]:
        """Lấy danh sách tất cả modules đã load"""
        return list(self.loaded_modules.values())

    def list_failed_modules(self) -> Dict[str, str]:
        """Lấy danh sách modules load thất bại (debugging)"""
        return self.failed_modules.copy()

    def get_all_models(self) -> Dict[str, List[str]]:
        """
        Lấy tất cả models từ tất cả modules
        
        Returns:
            Dict[module_name, [model_names]]
        """
        return {
            mod.name: mod.models
            for mod in self.loaded_modules.values()
        }
