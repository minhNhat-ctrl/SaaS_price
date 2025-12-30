from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
import uuid


class Tenant(TenantMixin):
    """
    SaaS Tenant - Multi-tenancy with Shared Database + Separate Schemas
    
    Kế thừa từ TenantMixin của django-tenants:
    - Tự động quản lý schema (create/drop)
    - Auto migration per tenant
    - Domain routing
    
    Attributes:
    - id: UUID primary key
    - name: Tên khách hàng / công ty
    - slug: Định danh duy nhất (URL-safe)
    - schema_name: PostgreSQL schema name (auto-generated từ slug)
    - status: active/suspended/deleted
    - created_at, updated_at: Timestamps
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    name = models.CharField(
        max_length=255,
        help_text="Tên khách hàng / công ty"
    )

    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Định danh tenant (dùng cho subdomain / internal ref)"
    )

    schema_name = models.CharField(
        max_length=63,
        unique=True,
        default="",
        help_text="PostgreSQL schema name (auto-generated từ slug)"
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("deleted", "Deleted"),
        ],
        default="active"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # Required by TenantMixin (inherited)
    # - schema_name: Automatically set dựa trên slug
    # - auto_create_schema: Create schema tự động
    auto_create_schema = True

    class Meta:
        db_table = "tenants"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Override save để auto-generate schema_name từ slug
        
        Schema naming convention: tenant_{slug}
        (django-tenants yêu cầu schema_name không có hyphens)
        """
        if not self.schema_name:
            # Thay hyphens bằng underscores (PostgreSQL schema requirement)
            self.schema_name = f"tenant_{self.slug.replace('-', '_')}"
        
        super().save(*args, **kwargs)


class TenantDomain(DomainMixin):
    """
    Domain / Subdomain mapping → Tenant
    
    Kế thừa từ DomainMixin của django-tenants:
    - Automatic domain routing
    - Support multiple domains per tenant
    
    Workflow:
    1. Request tới example.com hoặc tenant.example.com
    2. Django-tenants middleware resolve domain → tenant
    3. Set schema_name ở connection context
    4. ORM queries tự động sử dụng tenant schema
    """

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="domains"
    )

    domain = models.CharField(
        max_length=255,
        unique=True,
        help_text="example.com hoặc tenant.example.com"
    )

    is_primary = models.BooleanField(
        default=True,
        help_text="Primary domain cho tenant (subdomain routing)"
    )

    class Meta:
        db_table = "tenant_domains"

    def __str__(self):
        return self.domain
