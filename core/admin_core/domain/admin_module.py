"""
Domain Entity - AdminModule

Đại diện cho một module trong hệ thống với khả năng admin
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class AdminModule:
    """
    Admin Module Entity
    
    Đại diện cho một module trong platform có đăng ký django_admin.py
    
    Attributes:
        name: Tên module (ví dụ: 'core.tenants')
        app_label: Django app label
        verbose_name: Tên hiển thị
        description: Mô tả module
        models: Danh sách models được quản lý
        is_enabled: Module có active không
        admin_module_path: Đường dẫn tới django_admin.py
    """
    name: str
    app_label: str
    verbose_name: str
    description: str = ""
    models: List[str] = field(default_factory=list)
    is_enabled: bool = True
    admin_module_path: str = ""
    loaded_at: Optional[datetime] = None

    def __str__(self) -> str:
        return f"AdminModule(name={self.name}, label={self.app_label})"

    def is_loaded(self) -> bool:
        """Kiểm tra module đã được load chưa"""
        return self.loaded_at is not None

    def mark_loaded(self):
        """Đánh dấu module đã load"""
        self.loaded_at = datetime.now()

    def add_model(self, model_name: str):
        """Thêm model vào danh sách"""
        if model_name not in self.models:
            self.models.append(model_name)

    def has_model(self, model_name: str) -> bool:
        """Kiểm tra có model này không"""
        return model_name in self.models
