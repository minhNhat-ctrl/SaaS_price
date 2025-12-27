from django.db import models
import uuid


class Tenant(models.Model):
    """
    SaaS Tenant
    - Đại diện cho 1 khách hàng / 1 công ty
    - Do hệ thống quản trị tạo
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

    class Meta:
        db_table = "tenants"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.name
    
    
class TenantDomain(models.Model):
    """
    Mapping domain / subdomain → tenant
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
        default=True
    )

    class Meta:
        db_table = "tenant_domains"

    def __str__(self):
        return self.domain
