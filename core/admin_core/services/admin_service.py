"""
Admin Service - Business Logic & Use-case Implementation

Mục đích:
- Điều phối logic admin
- Validate hash + rate limiting
- Discover & load admin modules
- Nhận input thuần (không Django)
- Return domain objects

Nguyên tắc:
- KHÔNG import Django
- KHÔNG import request/response
- Gọi repository để truy cập data
- Gọi AdminHashService để quản lý hash (không validate ở đó)
"""
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from core.admin_core.domain import (
    AdminModule,
    AdminSecurityError,
    InvalidAdminHashError,
    AdminModuleLoadError,
)
from core.admin_core.services.admin_hash_service import AdminHashService
from core.admin_core.services.admin_module_loader import AdminModuleLoader


class AdminService:
    """
    Service layer cho Admin Core
    
    Điều phối:
    - Domain logic (validation)
    - AdminHashService (hash generation)
    - AdminModuleLoader (module discovery)
    - Security policy (rate limiting)
    
    Trách nhiệm:
    - Validate hash từ request (kết hợp hash service + rate limit logic)
    - Discover & load modules
    - Track failed attempts & rate limit
    - Lấy thông tin modules
    """

    def __init__(
        self,
        hash_service: AdminHashService,
        module_loader: AdminModuleLoader,
    ):
        """
        Dependency injection
        
        Args:
            hash_service: AdminHashService instance
            module_loader: AdminModuleLoader instance
        """
        self.hash_service = hash_service
        self.module_loader = module_loader
        
        # Rate limiting state
        self.failed_attempts: Dict[str, List[tuple]] = {}  # IP → [(ts, reason), ...]
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=30)

    async def validate_admin_hash(
        self,
        provided_hash: str,
        client_ip: Optional[str] = None,
    ) -> bool:
        """
        Use-case: Xác thực hash URL admin
        
        Quy trình:
        1. Check rate limit (dựa trên IP)
        2. So sánh hash (constant-time)
        3. Track failed attempts
        
        Args:
            provided_hash: Hash từ URL
            client_ip: IP của client
        
        Returns:
            True nếu hash hợp lệ, False nếu không
        
        Raises:
            AdminSecurityError: Nếu bị rate limit
        """
        # Check rate limit trước
        if client_ip and self._is_rate_limited(client_ip):
            raise AdminSecurityError(
                f"Too many failed attempts from {client_ip}. Please try again later."
            )

        # So sánh hash (sử dụng hash service)
        expected_hash = self.hash_service.get_hash()
        is_valid = self.hash_service.constant_time_compare(provided_hash, expected_hash)

        # Track failed attempt nếu invalid
        if not is_valid and client_ip:
            self._record_failed_attempt(client_ip, "invalid_hash")

        return is_valid

    async def discover_and_load_admin_modules(
        self,
        base_path: Optional[str] = None,
        modules_dir: str = "core",
    ) -> List[AdminModule]:
        """
        Use-case: Discover & load admin modules
        
        Workflow:
        1. Scan thư mục chứa modules
        2. Tìm django_admin.py
        3. Import module
        4. Track loaded modules
        
        Args:
            base_path: Base path của project
            modules_dir: Tên thư mục chứa modules
        
        Returns:
            Danh sách AdminModule đã load
        
        Raises:
            AdminModuleLoadError: Nếu có lỗi critical
        """
        return await self.module_loader.discover_and_load_modules(
            base_path=base_path,
            modules_dir=modules_dir,
        )

    async def get_loaded_modules(self) -> List[AdminModule]:
        """
        Use-case: Lấy danh sách modules đã load
        
        Returns:
            Danh sách AdminModule
        """
        return self.module_loader.list_modules()

    async def get_failed_modules(self) -> Dict[str, str]:
        """
        Use-case: Lấy danh sách modules load thất bại
        
        Returns:
            Dict[module_name] → error_reason
        """
        return self.module_loader.list_failed_modules()

    def get_admin_url(self, base_url: str = "") -> str:
        """
        Use-case: Lấy URL admin (with hash)
        
        Args:
            base_url: Base URL của site
        
        Returns:
            Đường dẫn admin đầy đủ
        """
        return self.hash_service.get_admin_url(base_url)

    def get_failed_attempts_for_ip(self, client_ip: str) -> int:
        """
        Use-case: Lấy số lượng failed attempts cho IP
        
        Args:
            client_ip: IP address
        
        Returns:
            Số lượng failed attempts (trong lockout window)
        """
        if client_ip not in self.failed_attempts:
            return 0

        now = datetime.now()
        valid_attempts = [
            (ts, reason) for ts, reason in self.failed_attempts[client_ip]
            if now - ts < self.lockout_duration
        ]
        
        return len(valid_attempts)

    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check xem IP có bị rate limit không"""
        if client_ip not in self.failed_attempts:
            return False

        attempts = self.failed_attempts[client_ip]
        
        # Clean up old attempts
        now = datetime.now()
        valid_attempts = [
            (ts, reason) for ts, reason in attempts
            if now - ts < self.lockout_duration
        ]
        
        self.failed_attempts[client_ip] = valid_attempts

        return len(valid_attempts) >= self.max_failed_attempts

    def _record_failed_attempt(self, client_ip: str, reason: str = ""):
        """Record một failed attempt"""
        if client_ip not in self.failed_attempts:
            self.failed_attempts[client_ip] = []

        self.failed_attempts[client_ip].append((datetime.now(), reason))

    def reset_failed_attempts(self, client_ip: str):
        """Reset failed attempts cho IP"""
        if client_ip in self.failed_attempts:
            del self.failed_attempts[client_ip]
