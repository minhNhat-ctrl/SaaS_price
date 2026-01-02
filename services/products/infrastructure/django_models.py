"""
Django Models for Products Module

Infrastructure layer - Django ORM implementation.
Implements tenant-aware and shared models.
"""
import uuid
import hashlib
from django.db import models
from django.contrib.postgres.indexes import GinIndex


# ============================================================
# Tenant Models (Tenant Schema)
# ============================================================

class TenantProduct(models.Model):
    """
    Tenant Product - Product managed by specific tenant.
    
    Lives in tenant schema via django-tenants.
    """
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ARCHIVED', 'Archived'),
        ('DRAFT', 'Draft'),
        ('DISCONTINUED', 'Discontinued'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True, help_text="Tenant ID (logical reference)")
    
    # Basic Info
    name = models.CharField(max_length=255, db_index=True)
    internal_code = models.CharField(max_length=100, blank=True, db_index=True)
    sku = models.CharField(max_length=100, blank=True, db_index=True, help_text="Tenant-defined SKU")
    barcode = models.CharField(max_length=100, blank=True, db_index=True)
    qr_code = models.CharField(max_length=255, blank=True)
    gtin = models.CharField(max_length=50, blank=True, db_index=True, help_text="Global Trade Item Number")
    
    # References
    brand = models.CharField(max_length=100, blank=True, db_index=True)
    category = models.CharField(max_length=100, blank=True, db_index=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', db_index=True)
    
    # Link to shared product
    shared_product_id = models.UUIDField(null=True, blank=True, db_index=True, help_text="Link to SharedProduct")
    
    # Custom attributes
    custom_attributes = models.JSONField(default=dict, blank=True)
    
    # Visibility
    is_public = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products_tenant_product'
        indexes = [
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['tenant_id', 'sku']),
            models.Index(fields=['tenant_id', 'gtin']),
            GinIndex(fields=['custom_attributes'], name='tenant_prod_custom_gin'),
        ]
        unique_together = [('tenant_id', 'sku')]
        ordering = ['-created_at']
        verbose_name = 'Tenant Product'
        verbose_name_plural = 'Tenant Products'
    
    def __str__(self):
        return f"{self.name} ({self.sku or self.id})"


# ============================================================
# Shared Models (Public Schema)
# ============================================================

class SharedProduct(models.Model):
    """
    Canonical Product - Normalized product across all tenants.
    
    Lives in public schema. Represents physical/standard product.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Standard identifiers
    gtin = models.CharField(max_length=50, unique=True, db_index=True, help_text="Global Trade Item Number")
    ean = models.CharField(max_length=50, blank=True, db_index=True, help_text="European Article Number")
    upc = models.CharField(max_length=50, blank=True, db_index=True, help_text="Universal Product Code")
    
    # Normalized info
    manufacturer = models.CharField(max_length=255, blank=True, db_index=True)
    normalized_name = models.CharField(max_length=500, blank=True, db_index=True)
    
    # Deduplication
    specs_hash = models.CharField(max_length=64, blank=True, db_index=True, help_text="Hash for deduplication")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products_shared_product'
        indexes = [
            models.Index(fields=['gtin', 'manufacturer']),
            models.Index(fields=['normalized_name']),
        ]
        ordering = ['-created_at']
        verbose_name = 'Shared Product'
        verbose_name_plural = 'Shared Products'
    
    def __str__(self):
        return f"{self.normalized_name or self.gtin}"


class SharedProductURL(models.Model):
    """
    Product URL - Marketplace/website URLs for shared products.
    
    Lives in public schema. One SharedProduct can have many URLs.
    """
    
    MARKETPLACE_CHOICES = [
        ('AMAZON', 'Amazon'),
        ('RAKUTEN', 'Rakuten'),
        ('SHOPEE', 'Shopee'),
        ('LAZADA', 'Lazada'),
        ('MANUFACTURER', 'Manufacturer Website'),
        ('CUSTOM', 'Custom'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_id = models.UUIDField(db_index=True, help_text="Reference to SharedProduct")
    
    # URL Info
    domain = models.CharField(max_length=255, db_index=True)
    full_url = models.TextField(help_text="Full product URL")
    # url_hash = models.CharField(max_length=64, unique=True, db_index=True, help_text="SHA256 hash of normalized URL for deduplication")  # Will add via migration
    marketplace_type = models.CharField(max_length=50, choices=MARKETPLACE_CHOICES, default='CUSTOM', db_index=True)
    
    # Price info
    currency = models.CharField(max_length=10, default='USD', db_index=True)
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Metadata
    meta = models.JSONField(default=dict, blank=True, help_text="Region, seller, variant, etc.")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products_shared_url'
        indexes = [
            models.Index(fields=['product_id', 'is_active']),
            models.Index(fields=['marketplace_type', 'is_active']),
            models.Index(fields=['domain', 'is_active']),
            GinIndex(fields=['meta'], name='shared_url_meta_gin'),
        ]
        ordering = ['-created_at']
        verbose_name = 'Product URL'
        verbose_name_plural = 'Product URLs'
    
    def __str__(self):
        return f"{self.domain} - {self.marketplace_type}"
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL for consistent hashing (lowercase, remove trailing slash)"""
        return url.lower().rstrip('/')
    
    @staticmethod
    def hash_url(url: str) -> str:
        """Generate SHA256 hash of normalized URL"""
        normalized = SharedProductURL.normalize_url(url)
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def save(self, *args, **kwargs):
        """Auto-generate url_hash before saving (disabled while url_hash column not in public schema)"""
        # Once url_hash column is available in public schema, uncomment this:
        # if not self.url_hash:
        #     self.url_hash = self.hash_url(self.full_url)
        super().save(*args, **kwargs)


class SharedPriceHistory(models.Model):
    """
    Price History - Time-series price data.
    
    Lives in public schema. Large volume, optimized for time-series queries.
    """
    
    SOURCE_CHOICES = [
        ('CRAWLER', 'Web Crawler'),
        ('API', 'API'),
        ('MANUAL', 'Manual Entry'),
        ('IMPORT', 'Bulk Import'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_url_id = models.UUIDField(db_index=True, help_text="Reference to SharedProductURL")
    
    # Price data
    price = models.DecimalField(max_digits=12, decimal_places=2, db_index=True)
    currency = models.CharField(max_length=10, default='USD', db_index=True)
    
    # Timestamp
    recorded_at = models.DateTimeField(db_index=True, help_text="When price was recorded")
    
    # Source
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='CRAWLER', db_index=True)
    
    # Optional metadata
    meta = models.JSONField(default=dict, blank=True, help_text="Discount, availability, etc.")
    
    class Meta:
        db_table = 'products_price_history'
        indexes = [
            models.Index(fields=['product_url_id', 'recorded_at']),
            models.Index(fields=['product_url_id', '-recorded_at']),  # For latest price
            models.Index(fields=['recorded_at', 'product_url_id']),  # For time-range queries
            GinIndex(fields=['meta'], name='price_hist_meta_gin'),
        ]
        ordering = ['-recorded_at']
        verbose_name = 'Price History'
        verbose_name_plural = 'Price History'
    
    def __str__(self):
        return f"{self.price} {self.currency} @ {self.recorded_at}"
