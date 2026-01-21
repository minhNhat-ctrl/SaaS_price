"""
Tenant Service - Business Logic / Use-case Implementation

Nguyên tắc:
- Không import Django
- Không import request, response
- Chỉ gọi repository để truy cập data
- Chỉ nhận input thuần (không phải HttpRequest)
- Return domain objects hoặc DTO (không phải Django Response)

Multi-tenancy:
- Mỗi create_tenant → auto-create schema
- Mỗi delete_tenant → auto-drop schema
- Repository handle schema switching
"""
from typing import Optional, List
from uuid import UUID
import logging

from core.tenants.domain import (
    Tenant,
    TenantStatus,
    TenantDomainValue,
    TenantNotFoundError,
    TenantAlreadyExistsError,
    InvalidTenantSlugError,
)
from core.tenants.repositories import TenantRepository

logger = logging.getLogger(__name__)


class TenantService:
    """
    Service layer cho Tenant
    
    Điều phối:
    - Domain entity logic
    - Repository data access
    - Business rule validation
    - Schema management (indirectly through Django-Tenants)
    """

    def __init__(self, repository: TenantRepository):
        """
        Dependency injection của repository
        
        Args:
            repository: Concrete implementation của TenantRepository
        """
        self.repository = repository

    async def create_tenant(
        self,
        name: str,
        slug: str,
        domain: str,
        is_primary: bool = True,
    ) -> Tenant:
        """
        Use-case: Tạo tenant mới
        
        Quy trình:
        1. Check slug đã tồn tại
        2. Tạo domain entity
        3. Tạo tenant entity (auto-generate schema_name)
        4. Lưu vào database (django-tenants auto-create schema)
        
        Args:
            name: Tên khách hàng / công ty
            slug: Định danh duy nhất (lowercase, alphanumeric + hyphens)
            domain: Domain chính của tenant
            is_primary: Domain này có là primary không (default True)
        
        Returns:
            Tenant entity vừa tạo
        
        Raises:
            InvalidTenantSlugError: Nếu slug không hợp lệ
            TenantAlreadyExistsError: Nếu slug đã tồn tại
            TenantDomainInvalidError: Nếu domain không hợp lệ
        """
        # Check slug đã tồn tại chưa
        existing = await self.repository.get_by_slug(slug)
        if existing:
            raise TenantAlreadyExistsError(slug)

        # Tạo domain value object
        domain_obj = TenantDomainValue(domain=domain, is_primary=is_primary)

        # Tạo tenant entity (domain layer sẽ validate + auto-generate schema_name)
        # Schema name format: tenant_{slug_with_underscores}
        schema_name = f"tenant_{slug.lower().replace('-', '_')}"
        
        tenant = Tenant.create(
            name=name,
            slug=slug,
            schema_name=schema_name,
            domains=[domain_obj],
            status=TenantStatus.ACTIVE,
        )

        # Lưu vào database (django-tenants tự động create schema)
        saved_tenant = await self.repository.create(tenant)
        
        logger.info(f"Tenant created: {name} (slug={slug}, schema={schema_name})")
        
        return saved_tenant

    async def get_tenant_by_id(self, tenant_id: UUID) -> Tenant:
        """
        Use-case: Lấy thông tin tenant theo ID
        
        Args:
            tenant_id: UUID của tenant
        
        Returns:
            Tenant entity
        
        Raises:
            TenantNotFoundError: Nếu tenant không tồn tại
        """
        tenant = await self.repository.get_by_id(tenant_id)
        if not tenant:
            raise TenantNotFoundError(tenant_id=str(tenant_id))
        return tenant

    async def get_tenant_by_slug(self, slug: str) -> Tenant:
        """
        Use-case: Lấy tenant theo slug
        
        Args:
            slug: Slug định danh của tenant
        
        Returns:
            Tenant entity
        
        Raises:
            TenantNotFoundError: Nếu tenant không tồn tại
        """
        tenant = await self.repository.get_by_slug(slug)
        if not tenant:
            raise TenantNotFoundError(slug=slug)
        return tenant

    async def get_tenant_by_domain(self, domain: str) -> Tenant:
        """
        Use-case: Lấy tenant theo domain
        
        Phục vụ middleware: resolve tenant từ request.META['HTTP_HOST']
        
        Workflow:
        1. Query Domain table
        2. Get Tenant từ Domain.tenant
        3. Return domain entity
        
        Args:
            domain: Domain từ HTTP request
        
        Returns:
            Tenant entity
        
        Raises:
            TenantNotFoundError: Nếu domain không tương ứng tenant nào
        """
        tenant = await self.repository.get_by_domain(domain)
        if not tenant:
            raise TenantNotFoundError(slug=domain)
        return tenant

    async def list_all_tenants(self, status: Optional[TenantStatus] = None) -> List[Tenant]:
        """
        Use-case: Lấy danh sách tất cả tenant (ADMIN ONLY)
        
        ⚠️ WARNING: Chỉ dùng cho admin/superuser
        User thường phải dùng application layer orchestrator để list tenants by user
        (ghép nối với access module để lấy memberships)
        
        Args:
            status: Lọc theo trạng thái (optional)
        
        Returns:
            Danh sách Tenant
        """
        return await self.repository.list_all(status=status)
    
    async def get_tenants_by_ids(self, tenant_ids: List[UUID], status: Optional[TenantStatus] = None) -> List[Tenant]:
        """
        Use-case: Lấy danh sách tenant theo list IDs
        
        Dùng bởi application layer để load tenants sau khi lấy tenant_ids từ memberships
        
        Args:
            tenant_ids: Danh sách UUID của tenants
            status: Lọc theo trạng thái (optional)
        
        Returns:
            Danh sách Tenant
        """
        tenants = []
        for tenant_id in tenant_ids:
            try:
                tenant = await self.repository.get_by_id(tenant_id)
                if tenant:
                    # Filter by status if specified
                    if status is None or tenant.status == status:
                        tenants.append(tenant)
            except Exception as e:
                logger.warning(f"Failed to load tenant {tenant_id}: {e}")
                continue
        
        return tenants

    async def update_tenant_info(
        self,
        tenant_id: UUID,
        name: Optional[str] = None,
    ) -> Tenant:
        """
        Use-case: Cập nhật thông tin tenant
        
        Args:
            tenant_id: UUID của tenant
            name: Tên mới (optional)
        
        Returns:
            Tenant entity sau khi update
        
        Raises:
            TenantNotFoundError: Nếu tenant không tồn tại
        """
        tenant = await self.get_tenant_by_id(tenant_id)

        if name:
            tenant.name = name.strip()

        return await self.repository.update(tenant)

    async def activate_tenant(self, tenant_id: UUID) -> Tenant:
        """
        Use-case: Kích hoạt tenant (active)
        
        Args:
            tenant_id: UUID của tenant
        
        Returns:
            Tenant entity sau khi activate
        
        Raises:
            TenantNotFoundError: Nếu tenant không tồn tại
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        tenant.activate()
        
        logger.info(f"Tenant activated: {tenant.slug}")
        
        return await self.repository.update(tenant)

    async def suspend_tenant(self, tenant_id: UUID) -> Tenant:
        """
        Use-case: Tạm dừng dịch vụ tenant (suspend)
        
        Args:
            tenant_id: UUID của tenant
        
        Returns:
            Tenant entity sau khi suspend
        
        Raises:
            TenantNotFoundError: Nếu tenant không tồn tại
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        tenant.suspend()
        
        logger.info(f"Tenant suspended: {tenant.slug}")
        
        return await self.repository.update(tenant)

    async def delete_tenant(self, tenant_id: UUID) -> bool:
        """
        Use-case: Xóa tenant (soft delete)
        
        Notes:
        - Soft delete (status = deleted)
        - Schema vẫn tồn tại (bảo toàn data)
        - Dùng django-tenants command để drop schema nếu cần
        
        Args:
            tenant_id: UUID của tenant
        
        Returns:
            True nếu xóa thành công
        
        Raises:
            TenantNotFoundError: Nếu tenant không tồn tại
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        tenant.delete()
        await self.repository.update(tenant)
        
        logger.warning(f"Tenant deleted (soft): {tenant.slug} (schema={tenant.schema_name})")
        logger.warning(f"To drop schema manually: psql -c 'DROP SCHEMA {tenant.schema_name} CASCADE;'")
        
        return True

    async def add_domain_to_tenant(
        self,
        tenant_id: UUID,
        domain: str,
        is_primary: bool = False,
    ) -> Tenant:
        """
        Use-case: Thêm domain mới cho tenant
        
        Args:
            tenant_id: UUID của tenant
            domain: Domain mới
            is_primary: Domain này có thay thế primary không
        
        Returns:
            Tenant entity sau khi add domain
        
        Raises:
            TenantNotFoundError: Nếu tenant không tồn tại
            TenantDomainInvalidError: Nếu domain không hợp lệ hoặc đã tồn tại
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        
        domain_obj = TenantDomainValue(domain=domain, is_primary=is_primary)
        tenant.add_domain(domain_obj)
        
        logger.info(f"Domain added to tenant {tenant.slug}: {domain}")
        
        return await self.repository.update(tenant)

    async def tenant_exists(self, tenant_id: UUID) -> bool:
        """
        Use-case: Kiểm tra tenant có tồn tại không
        
        Args:
            tenant_id: UUID của tenant
        
        Returns:
            True nếu tồn tại, False nếu không
        """
        return await self.repository.exists(tenant_id)

    async def count_active_tenants(self) -> int:
        """
        Use-case: Đếm số lượng tenant đang hoạt động
        
        Returns:
            Số lượng tenant active
        """
        return await self.repository.count_by_status(TenantStatus.ACTIVE)
