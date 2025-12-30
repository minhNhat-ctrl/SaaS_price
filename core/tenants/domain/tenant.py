"""
Domain Entity - Tenant

Pure business logic, không import Django hay bất kỳ framework nào
"""
import re
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from uuid import UUID, uuid4

from .exceptions import InvalidTenantSlugError, TenantDomainInvalidError


class TenantStatus(Enum):
    """Trạng thái của Tenant"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


@dataclass
class TenantDomainValue:
    """
    Value Object - Domain của Tenant
    
    Đại diện cho mapping domain/subdomain → tenant
    """
    domain: str
    is_primary: bool = True

    def __post_init__(self):
        if not self._is_valid_domain(self.domain):
            raise TenantDomainInvalidError(self.domain)

    @staticmethod
    def _is_valid_domain(domain: str) -> bool:
        """
        Validate domain format (RFC 1123)
        Chấp nhận: example.com, subdomain.example.com, tenant-app.example.com
        """
        if not domain or len(domain) > 255:
            return False
        
        # Simple validation - có thể mở rộng thêm regex phức tạp
        pattern = r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9]{2,}$'
        return bool(re.match(pattern, domain.lower()))


@dataclass
class Tenant:
    """
    Domain Entity - Tenant
    
    Đại diện cho một khách hàng / công ty trên platform SaaS
    
    Nguyên tắc:
    - Không import Django
    - Không biết về DB, ORM, HTTP
    - Chỉ chứa business logic
    
    Multi-tenancy:
    - Mỗi tenant có schema riêng (PostgreSQL schema)
    - schema_name dùng để identify schema trong database
    - Format: tenant_{slug}
    """
    id: UUID
    name: str
    slug: str
    status: TenantStatus
    schema_name: str  # PostgreSQL schema name (e.g., 'tenant_acme')
    domains: List[TenantDomainValue] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate tenant data"""
        self._validate_slug()
        self._ensure_primary_domain()

    def _validate_slug(self):
        """
        Validate slug format
        - Lowercase alphanumeric + hyphens
        - 3-100 characters
        """
        pattern = r'^[a-z0-9](?:[a-z0-9-]{1,98}[a-z0-9])?$'
        if not re.match(pattern, self.slug):
            raise InvalidTenantSlugError(self.slug)

    def _ensure_primary_domain(self):
        """Đảm bảo có ít nhất 1 primary domain"""
        primary_domains = [d for d in self.domains if d.is_primary]
        if len(primary_domains) > 1:
            # Chỉ giữ primary domain đầu tiên
            for i, domain in enumerate(self.domains):
                domain.is_primary = (i == primary_domains[0])

    @classmethod
    def create(
        cls,
        name: str,
        slug: str,
        schema_name: str,
        domains: List[TenantDomainValue],
        status: TenantStatus = TenantStatus.ACTIVE,
    ) -> "Tenant":
        """
        Factory method để tạo tenant mới
        
        Args:
            name: Tên khách hàng / công ty
            slug: Định danh duy nhất (lowercase, alphanumeric + hyphens)
            schema_name: PostgreSQL schema name (e.g., 'tenant_acme')
            domains: Danh sách domain
            status: Trạng thái (mặc định ACTIVE)
        
        Returns:
            Tenant entity
        
        Raises:
            InvalidTenantSlugError: Nếu slug không hợp lệ
            TenantDomainInvalidError: Nếu domain không hợp lệ
        """
        tenant = cls(
            id=uuid4(),
            name=name.strip(),
            slug=slug.strip().lower(),
            schema_name=schema_name.strip().lower(),
            status=status,
            domains=domains,
        )
        return tenant

    def activate(self):
        """Activate tenant"""
        self.status = TenantStatus.ACTIVE
        self.updated_at = datetime.now()

    def suspend(self):
        """Suspend tenant"""
        self.status = TenantStatus.SUSPENDED
        self.updated_at = datetime.now()

    def delete(self):
        """Soft delete tenant"""
        self.status = TenantStatus.DELETED
        self.updated_at = datetime.now()

    def add_domain(self, domain: TenantDomainValue):
        """
        Thêm domain mới cho tenant
        
        Args:
            domain: TenantDomainValue
        """
        # Kiểm tra domain đã tồn tại
        if any(d.domain == domain.domain for d in self.domains):
            raise TenantDomainInvalidError(f"Domain {domain.domain} already exists")
        
        # Nếu domain mới là primary, bỏ primary từ domain cũ
        if domain.is_primary:
            for d in self.domains:
                d.is_primary = False
        
        self.domains.append(domain)
        self.updated_at = datetime.now()

    def is_active(self) -> bool:
        """Kiểm tra tenant có active không"""
        return self.status == TenantStatus.ACTIVE

    def __str__(self) -> str:
        return f"Tenant(id={self.id}, name={self.name}, slug={self.slug})"
