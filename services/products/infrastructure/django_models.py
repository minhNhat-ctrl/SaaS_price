"""
Django Models for Products Module (Tenant Data)

Infrastructure layer - Django ORM implementation.
These models live in TENANT schema.

For shared data (Domain, ProductURL, PriceHistory), see services.products_shared.
"""
import uuid
from django.db import models
from django.contrib.postgres.indexes import GinIndex


class Product(models.Model):
    """
    Tenant Product - Product owned by a specific tenant.
    
    Lives in TENANT schema.
    Full CRUD by tenant owner.
    SKU and GTIN must be unique per tenant.
    """
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ARCHIVED', 'Archived'),
        ('DRAFT', 'Draft'),
        ('DISCONTINUED', 'Discontinued'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True, help_text="Tenant ID (denormalized for queries)")
    
    # Product Identifiers (unique per tenant)
    name = models.CharField(max_length=255, db_index=True)
    sku = models.CharField(
        max_length=100, 
        blank=True, 
        default='',
        db_index=True, 
        help_text="Stock Keeping Unit - unique per tenant"
    )
    gtin = models.CharField(
        max_length=50, 
        blank=True, 
        default='',
        db_index=True, 
        help_text="Global Trade Item Number - unique per tenant"
    )
    internal_code = models.CharField(max_length=100, blank=True, default='')
    barcode = models.CharField(max_length=100, blank=True, default='')
    qr_code = models.CharField(max_length=255, blank=True, default='')
    
    # Product Info
    brand = models.CharField(max_length=100, blank=True, default='', db_index=True)
    category = models.CharField(max_length=100, blank=True, default='', db_index=True)
    description = models.TextField(blank=True, default='')
    
    # Status
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='DRAFT', 
        db_index=True
    )
    is_public = models.BooleanField(default=False)
    
    # Extensibility
    custom_attributes = models.JSONField(default=dict, blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'products'
        db_table = 'products_product'
        indexes = [
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['tenant_id', 'name']),
            models.Index(fields=['tenant_id', 'sku']),
            models.Index(fields=['tenant_id', 'gtin']),
            GinIndex(fields=['custom_attributes'], name='product_custom_attrs_gin'),
        ]
        constraints = [
            # Unique SKU per tenant (excluding empty strings)
            models.UniqueConstraint(
                fields=['tenant_id', 'sku'],
                name='unique_sku_per_tenant',
                condition=~models.Q(sku='')
            ),
            # Unique GTIN per tenant (excluding empty strings)
            models.UniqueConstraint(
                fields=['tenant_id', 'gtin'],
                name='unique_gtin_per_tenant',
                condition=~models.Q(gtin='')
            ),
        ]
        ordering = ['-created_at']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
    
    def __str__(self):
        return f"{self.name} ({self.sku or self.id})"


class ProductURLMapping(models.Model):
    """
    Product URL Mapping - Links tenant's Product to shared ProductURL.
    
    Lives in TENANT schema.
    References shared ProductURL via url_hash (not FK, cross-schema safe).
    
    Constraints:
    - A tenant can only add the same URL once (regardless of which product)
    - url_hash is unique within tenant schema
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Product reference (same schema)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='url_mappings',
        help_text="Product this URL belongs to"
    )
    
    # Reference to shared ProductURL (by hash, not FK)
    url_hash = models.CharField(
        max_length=64, 
        db_index=True,
        help_text="SHA-256 hash referencing ProductURL in public schema"
    )
    
    # Tenant-specific metadata for this URL
    custom_label = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        help_text="Tenant's custom label for this URL"
    )
    is_primary = models.BooleanField(
        default=False, 
        help_text="Primary URL for this product"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Display order in product detail"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'products'
        db_table = 'products_url_mapping'
        indexes = [
            models.Index(fields=['product', 'is_primary']),
            models.Index(fields=['url_hash']),
        ]
        constraints = [
            # A product cannot have the same URL mapped twice
            models.UniqueConstraint(
                fields=['product', 'url_hash'],
                name='unique_url_per_product'
            ),
        ]
        ordering = ['display_order', '-created_at']
        verbose_name = 'Product URL Mapping'
        verbose_name_plural = 'Product URL Mappings'
    
    def __str__(self):
        return f"Product {self.product_id} -> URL {self.url_hash[:16]}..."
