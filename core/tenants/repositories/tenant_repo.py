"""
Tenant Repository - Abstract interface for data access

Không chứa logic, chỉ định nghĩa interface
Implementation sẽ ở infrastructure layer (Django ORM)
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from core.tenants.domain import Tenant, TenantStatus


class TenantRepository(ABC):
    """
    Abstract repository interface cho Tenant
    
    Mục đích: Che giấu chi tiết DB implementation (Django ORM)
    Cho phép swap DB provider sau này (chuyển từ Django ORM → SQLAlchemy, etc.)
    """

    @abstractmethod
    async def create(self, tenant: Tenant) -> Tenant:
        """
        Lưu tenant mới
        
        Args:
            tenant: Tenant entity
        
        Returns:
            Tenant (với ID và timestamps được populate)
        
        Raises:
            TenantAlreadyExistsError: Nếu slug đã tồn tại
        """
        pass

    @abstractmethod
    async def get_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        """
        Lấy tenant theo ID
        
        Args:
            tenant_id: UUID của tenant
        
        Returns:
            Tenant hoặc None nếu không tìm thấy
        """
        pass

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """
        Lấy tenant theo slug
        
        Args:
            slug: Slug định danh của tenant
        
        Returns:
            Tenant hoặc None nếu không tìm thấy
        """
        pass

    @abstractmethod
    async def get_by_domain(self, domain: str) -> Optional[Tenant]:
        """
        Lấy tenant theo domain
        
        Args:
            domain: Domain của tenant (ví dụ: example.com, tenant.example.com)
        
        Returns:
            Tenant hoặc None nếu không tìm thấy
        """
        pass

    @abstractmethod
    async def list_all(self, status: Optional[TenantStatus] = None) -> List[Tenant]:
        """
        Lấy danh sách tất cả tenant
        
        Args:
            status: Lọc theo trạng thái (optional)
        
        Returns:
            Danh sách Tenant
        """
        pass

    @abstractmethod
    async def update(self, tenant: Tenant) -> Tenant:
        """
        Cập nhật tenant
        
        Args:
            tenant: Tenant entity (với những thay đổi)
        
        Returns:
            Tenant (sau khi update)
        """
        pass

    @abstractmethod
    async def delete(self, tenant_id: UUID) -> bool:
        """
        Xóa tenant (soft delete hoặc hard delete)
        
        Args:
            tenant_id: UUID của tenant
        
        Returns:
            True nếu xóa thành công, False nếu không tìm thấy
        """
        pass

    @abstractmethod
    async def exists(self, tenant_id: UUID) -> bool:
        """
        Kiểm tra tenant có tồn tại không
        
        Args:
            tenant_id: UUID của tenant
        
        Returns:
            True nếu tồn tại, False nếu không
        """
        pass

    @abstractmethod
    async def count_by_status(self, status: TenantStatus) -> int:
        """
        Đếm số lượng tenant theo trạng thái
        
        Args:
            status: Trạng thái để đếm
        
        Returns:
            Số lượng tenant
        """
        pass
