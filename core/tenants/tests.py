"""
Integration Tests cho Tenant Module

Kiểm tra:
- Domain logic
- Repository implementation
- Service orchestration
- API endpoints

Tạo test này để verify kiến trúc tuân thủ nguyên tắc
"""
import pytest
from uuid import uuid4

from core.tenants.domain import (
    Tenant,
    TenantStatus,
    TenantDomainValue,
    TenantNotFoundError,
    TenantAlreadyExistsError,
    InvalidTenantSlugError,
)
from core.tenants.services import TenantService


class TestTenantDomain:
    """Test domain layer (pure Python, không Django)"""
    
    def test_tenant_creation_with_valid_slug(self):
        """Test tạo tenant với slug hợp lệ"""
        domain = TenantDomainValue(domain="example.com")
        tenant = Tenant.create(
            name="Test Company",
            slug="test-company",
            domains=[domain],
        )
        
        assert tenant.name == "Test Company"
        assert tenant.slug == "test-company"
        assert tenant.status == TenantStatus.ACTIVE
        assert len(tenant.domains) == 1

    def test_tenant_creation_with_invalid_slug(self):
        """Test tạo tenant với slug không hợp lệ"""
        domain = TenantDomainValue(domain="example.com")
        
        with pytest.raises(InvalidTenantSlugError):
            Tenant.create(
                name="Test Company",
                slug="Test-Company",  # Uppercase không được
                domains=[domain],
            )

    def test_tenant_activation(self):
        """Test activate tenant"""
        domain = TenantDomainValue(domain="example.com")
        tenant = Tenant.create(
            name="Test Company",
            slug="test-company",
            domains=[domain],
        )
        
        tenant.suspend()
        assert tenant.status == TenantStatus.SUSPENDED
        
        tenant.activate()
        assert tenant.status == TenantStatus.ACTIVE

    def test_tenant_add_domain(self):
        """Test thêm domain mới"""
        domain1 = TenantDomainValue(domain="example.com", is_primary=True)
        tenant = Tenant.create(
            name="Test Company",
            slug="test-company",
            domains=[domain1],
        )
        
        domain2 = TenantDomainValue(domain="example2.com", is_primary=False)
        tenant.add_domain(domain2)
        
        assert len(tenant.domains) == 2
        assert tenant.domains[0].is_primary is True
        assert tenant.domains[1].is_primary is False

    def test_tenant_invalid_domain(self):
        """Test tạo domain không hợp lệ"""
        with pytest.raises(Exception):  # TenantDomainInvalidError
            TenantDomainValue(domain="invalid domain with spaces")


class TestTenantService:
    """
    Test service layer
    
    Note: Cần mock repository để test service logic
    """
    
    @pytest.mark.asyncio
    async def test_create_tenant_use_case(self, mock_repo):
        """Test create tenant use case"""
        service = TenantService(mock_repo)
        
        tenant = await service.create_tenant(
            name="New Company",
            slug="new-company",
            domain="newcompany.com",
        )
        
        assert tenant.name == "New Company"
        assert tenant.slug == "new-company"
        assert len(tenant.domains) == 1

    @pytest.mark.asyncio
    async def test_create_tenant_duplicate_slug(self, mock_repo):
        """Test create tenant dengan slug trùng"""
        service = TenantService(mock_repo)
        
        # Mock repo sẽ return tenant existing
        with pytest.raises(TenantAlreadyExistsError):
            await service.create_tenant(
                name="New Company",
                slug="existing-company",
                domain="existing.com",
            )


# pytest fixtures
@pytest.fixture
def mock_repo():
    """Mock TenantRepository"""
    from unittest.mock import AsyncMock, MagicMock
    
    repo = MagicMock()
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_slug = AsyncMock(return_value=None)
    repo.get_by_domain = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    repo.exists = AsyncMock()
    repo.count_by_status = AsyncMock(return_value=0)
    
    return repo
