"""
Django ORM Implementation of TenantRepository

Concrete implementation sử dụng Django ORM
Che giấu chi tiết Django implementation khỏi service layer
"""
from typing import Optional, List
from uuid import UUID

from platform.tenants.domain import (
    Tenant,
    TenantStatus,
    TenantDomainValue,
    TenantNotFoundError,
    TenantAlreadyExistsError,
)
from platform.tenants.repositories import TenantRepository
from .django_models import Tenant as TenantModel, TenantDomain as TenantDomainModel


class DjangoTenantRepository(TenantRepository):
    """
    Concrete implementation của TenantRepository sử dụng Django ORM
    
    Trách nhiệm:
    - Convert Django ORM models ↔ Domain entities
    - Implement CRUD operations
    - Handle database transactions
    """

    def _dto_to_domain(self, db_tenant: TenantModel) -> Tenant:
        """
        Convert Django ORM model → Domain entity
        
        Args:
            db_tenant: Django TenantModel
        
        Returns:
            Domain Tenant entity
        """
        # Load domains
        domains = [
            TenantDomainValue(
                domain=td.domain,
                is_primary=td.is_primary,
            )
            for td in db_tenant.domains.all()
        ]

        return Tenant(
            id=db_tenant.id,
            name=db_tenant.name,
            slug=db_tenant.slug,
            status=TenantStatus(db_tenant.status),
            domains=domains,
            created_at=db_tenant.created_at,
            updated_at=db_tenant.updated_at,
        )

    def _domain_to_dto(self, tenant: Tenant) -> TenantModel:
        """
        Convert Domain entity → Django ORM model
        
        Args:
            tenant: Domain Tenant entity
        
        Returns:
            Django TenantModel
        """
        db_tenant = TenantModel(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            status=tenant.status.value,
        )
        return db_tenant

    async def create(self, tenant: Tenant) -> Tenant:
        """
        Lưu tenant mới vào database
        
        Args:
            tenant: Domain Tenant entity
        
        Returns:
            Domain Tenant entity (với ID, timestamps)
        
        Raises:
            TenantAlreadyExistsError: Nếu slug đã tồn tại
        """
        # Check slug đã tồn tại chưa
        if await TenantModel.objects.filter(slug=tenant.slug).aexists():
            raise TenantAlreadyExistsError(tenant.slug)

        # Convert domain → Django model
        db_tenant = self._domain_to_dto(tenant)
        
        # Lưu tenant
        await db_tenant.asave()

        # Lưu domains
        for domain in tenant.domains:
            await TenantDomainModel.objects.acreate(
                tenant=db_tenant,
                domain=domain.domain,
                is_primary=domain.is_primary,
            )

        # Return domain entity
        return await self.get_by_id(db_tenant.id)

    async def get_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        """
        Lấy tenant theo ID
        
        Args:
            tenant_id: UUID của tenant
        
        Returns:
            Domain Tenant entity hoặc None
        """
        try:
            db_tenant = await TenantModel.objects.prefetch_related('domains').aget(id=tenant_id)
            return self._dto_to_domain(db_tenant)
        except TenantModel.DoesNotExist:
            return None

    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """
        Lấy tenant theo slug
        
        Args:
            slug: Slug định danh
        
        Returns:
            Domain Tenant entity hoặc None
        """
        try:
            db_tenant = await TenantModel.objects.prefetch_related('domains').aget(slug=slug)
            return self._dto_to_domain(db_tenant)
        except TenantModel.DoesNotExist:
            return None

    async def get_by_domain(self, domain: str) -> Optional[Tenant]:
        """
        Lấy tenant theo domain
        
        Args:
            domain: Domain của tenant
        
        Returns:
            Domain Tenant entity hoặc None
        """
        try:
            tenant_domain = await TenantDomainModel.objects.select_related('tenant').aget(domain=domain)
            return await self.get_by_id(tenant_domain.tenant_id)
        except TenantDomainModel.DoesNotExist:
            return None

    async def list_all(self, status: Optional[TenantStatus] = None) -> List[Tenant]:
        """
        Lấy danh sách tenant
        
        Args:
            status: Lọc theo trạng thái (optional)
        
        Returns:
            Danh sách Domain Tenant entities
        """
        query = TenantModel.objects.prefetch_related('domains')
        
        if status:
            query = query.filter(status=status.value)
        
        db_tenants = await query.aall()
        return [self._dto_to_domain(db_tenant) for db_tenant in db_tenants]

    async def update(self, tenant: Tenant) -> Tenant:
        """
        Cập nhật tenant
        
        Args:
            tenant: Domain Tenant entity (với những thay đổi)
        
        Returns:
            Domain Tenant entity (sau khi update)
        """
        db_tenant = await TenantModel.objects.aget(id=tenant.id)
        
        # Update fields
        db_tenant.name = tenant.name
        db_tenant.slug = tenant.slug
        db_tenant.status = tenant.status.value
        
        await db_tenant.asave()

        # Update domains
        # Xóa domains cũ
        await TenantDomainModel.objects.filter(tenant=db_tenant).adelete()
        
        # Tạo domains mới
        for domain in tenant.domains:
            await TenantDomainModel.objects.acreate(
                tenant=db_tenant,
                domain=domain.domain,
                is_primary=domain.is_primary,
            )

        return await self.get_by_id(tenant.id)

    async def delete(self, tenant_id: UUID) -> bool:
        """
        Xóa tenant (hard delete hoặc soft delete tùy thiết kế)
        
        Args:
            tenant_id: UUID của tenant
        
        Returns:
            True nếu xóa thành công, False nếu không tìm thấy
        """
        try:
            db_tenant = await TenantModel.objects.aget(id=tenant_id)
            await db_tenant.adelete()
            return True
        except TenantModel.DoesNotExist:
            return False

    async def exists(self, tenant_id: UUID) -> bool:
        """
        Kiểm tra tenant tồn tại
        
        Args:
            tenant_id: UUID của tenant
        
        Returns:
            True nếu tồn tại, False nếu không
        """
        return await TenantModel.objects.filter(id=tenant_id).aexists()

    async def count_by_status(self, status: TenantStatus) -> int:
        """
        Đếm tenant theo trạng thái
        
        Args:
            status: Trạng thái để đếm
        
        Returns:
            Số lượng tenant
        """
        return await TenantModel.objects.filter(status=status.value).acount()
