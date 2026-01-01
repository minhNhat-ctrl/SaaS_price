"""
Django ORM Implementation of TenantRepository

Concrete implementation sử dụng Django ORM + django-tenants
Che giấu chi tiết Django implementation khỏi service layer

Multi-tenancy:
- Queries tự động filter theo schema (django-tenants handles)
- Tenant model kế thừa từ TenantMixin
- Domain model kế thừa từ DomainMixin
"""
from typing import Optional, List
from uuid import UUID
from asgiref.sync import sync_to_async

from core.tenants.domain import (
    Tenant,
    TenantStatus,
    TenantDomainValue,
    TenantNotFoundError,
    TenantAlreadyExistsError,
)
from core.tenants.repositories import TenantRepository
from .django_models import Tenant as TenantModel, TenantDomain as DomainModel


class DjangoTenantRepository(TenantRepository):
    """
    Concrete implementation của TenantRepository sử dụng Django ORM
    
    Trách nhiệm:
    - Convert Django ORM models ↔ Domain entities
    - Implement CRUD operations
    - Handle database transactions
    - Work with django-tenants schema context
    """

    async def _dto_to_domain(self, db_tenant: TenantModel) -> Tenant:
        """
        Convert Django ORM model → Domain entity (async safe)
        
        Args:
            db_tenant: Django TenantModel (từ django-tenants)
        
        Returns:
            Domain Tenant entity
        """
        # Load domains in a thread-safe way
        db_domains = await sync_to_async(list)(
            DomainModel.objects.filter(tenant=db_tenant)
        )

        domains = [
            TenantDomainValue(domain=d.domain, is_primary=d.is_primary)
            for d in db_domains
        ]

        return Tenant(
            id=db_tenant.id,
            name=db_tenant.name,
            slug=db_tenant.slug,
            schema_name=db_tenant.schema_name,
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
            schema_name=tenant.schema_name,
            status=tenant.status.value,
        )
        return db_tenant

    async def create(self, tenant: Tenant) -> Tenant:
        """
        Lưu tenant mới vào database
        
        Quy trình:
        1. Check slug đã tồn tại
        2. Create Tenant (tự động create schema)
        3. Create Domain mapping
        4. Return domain entity
        
        Args:
            tenant: Domain Tenant entity
        
        Returns:
            Domain Tenant entity (với ID, timestamps)
        
        Raises:
            TenantAlreadyExistsError: Nếu slug đã tồn tại
        
        Notes:
        - Django-tenants tự động create schema khi save
        - auto_create_schema=True ở TenantModel
        """
        # Check slug đã tồn tại chưa
        if await TenantModel.objects.filter(slug=tenant.slug).aexists():
            raise TenantAlreadyExistsError(tenant.slug)

        # Convert domain → Django model
        db_tenant = self._domain_to_dto(tenant)
        
        # Lưu tenant (django-tenants tự động create schema)
        await db_tenant.asave()

        # Lưu domains
        for domain in tenant.domains:
            await DomainModel.objects.acreate(
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
            db_tenant = await sync_to_async(TenantModel.objects.get)(id=tenant_id)
        except TenantModel.DoesNotExist:
            return None

        return await self._dto_to_domain(db_tenant)

    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """
        Lấy tenant theo slug
        
        Args:
            slug: Slug định danh
        
        Returns:
            Domain Tenant entity hoặc None
        """
        try:
            db_tenant = await sync_to_async(TenantModel.objects.get)(slug=slug)
            return await self._dto_to_domain(db_tenant)
        except TenantModel.DoesNotExist:
            return None

    async def get_by_domain(self, domain: str) -> Optional[Tenant]:
        """
        Lấy tenant theo domain
        
        Workflow:
        1. Tìm Domain matching domain string
        2. Get Tenant từ Domain.tenant
        
        Args:
            domain: Domain của tenant
        
        Returns:
            Domain Tenant entity hoặc None
        """
        try:
            domain_obj = await sync_to_async(
                DomainModel.objects.select_related('tenant').get
            )(domain=domain)
            return await self.get_by_id(domain_obj.tenant_id)
        except DomainModel.DoesNotExist:
            return None

    async def list_all(self, status: Optional[TenantStatus] = None) -> List[Tenant]:
        """
        Lấy danh sách tenant
        
        Args:
            status: Lọc theo trạng thái (optional)
        
        Returns:
            Danh sách Domain Tenant entities
        """
        query = TenantModel.objects.all()
        if status:
            query = query.filter(status=status.value)

        db_tenants = await sync_to_async(list)(query)

        tenants: List[Tenant] = []
        for db_tenant in db_tenants:
            tenants.append(await self._dto_to_domain(db_tenant))

        return tenants

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
        await DomainModel.objects.filter(tenant=db_tenant).adelete()
        
        # Tạo domains mới
        for domain in tenant.domains:
            await DomainModel.objects.acreate(
                tenant=db_tenant,
                domain=domain.domain,
                is_primary=domain.is_primary,
            )

        return await self.get_by_id(tenant.id)

    async def delete(self, tenant_id: UUID) -> bool:
        """
        Xóa tenant (soft delete)
        
        Notes:
        - Django-tenants tự động drop schema khi delete
        
        Args:
            tenant_id: UUID của tenant
        
        Returns:
            True nếu xóa thành công, False nếu không tìm thấy
        """
        try:
            db_tenant = await TenantModel.objects.aget(id=tenant_id)
            # Soft delete (set status = deleted)
            db_tenant.status = TenantStatus.DELETED.value
            await db_tenant.asave()
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
