"""
Shared Django Models

Django ORM models for PUBLIC schema.
These tables exist only in the public schema and are shared across all tenants.
"""
import uuid
from django.db import models


class Domain(models.Model):
    """
    Domain model - website domain configuration for crawling.
    
    Stored in PUBLIC schema.
    """
    
    class Meta:
        app_label = 'products_shared'
        db_table = 'products_domain'
        verbose_name = 'Domain'
        verbose_name_plural = 'Domains'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, db_index=True)  # e.g., amazon.co.jp
    
    # Crawl configuration
    crawl_enabled = models.BooleanField(default=True)
    crawl_interval_hours = models.IntegerField(default=24)
    rate_limit_per_minute = models.IntegerField(default=10)
    
    # Parser configuration
    parser_class = models.CharField(max_length=255, blank=True, default='')
    parser_config = models.JSONField(default=dict, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_health_check = models.DateTimeField(null=True, blank=True)
    health_status = models.CharField(max_length=20, default='OK')  # OK, DEGRADED, DOWN
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


class ProductURL(models.Model):
    """
    ProductURL model - unique product URLs deduplicated by hash.
    
    Stored in PUBLIC schema.
    Referenced by tenant's ProductURLMapping via url_hash.
    """
    
    class Meta:
        app_label = 'products_shared'
        db_table = 'products_url'
        verbose_name = 'Product URL'
        verbose_name_plural = 'Product URLs'
        indexes = [
            models.Index(fields=['domain']),
            models.Index(fields=['is_active', 'reference_count']),
            models.Index(fields=['last_crawled_at']),
        ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url_hash = models.CharField(max_length=64, unique=True, db_index=True)  # SHA-256
    
    # URL data
    raw_url = models.TextField()
    normalized_url = models.TextField()
    
    # Domain reference
    domain = models.ForeignKey(
        Domain,
        on_delete=models.PROTECT,
        related_name='urls'
    )
    
    # Reference counting
    reference_count = models.IntegerField(default=0, db_index=True)
    
    # Crawl status
    is_active = models.BooleanField(default=True)
    last_crawled_at = models.DateTimeField(null=True, blank=True)
    crawl_error = models.TextField(blank=True, default='')
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.domain.name}: {self.raw_url[:50]}..."


class PriceHistory(models.Model):
    """
    PriceHistory model - historical price records.
    
    Stored in PUBLIC schema.
    Append-only - no updates or deletes allowed.
    """
    
    class Meta:
        app_label = 'products_shared'
        db_table = 'products_price_history'
        verbose_name = 'Price History'
        verbose_name_plural = 'Price Histories'
        ordering = ['-scraped_at']
        indexes = [
            models.Index(fields=['product_url', 'scraped_at']),
            models.Index(fields=['scraped_at']),
        ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_url = models.ForeignKey(
        ProductURL,
        on_delete=models.CASCADE,
        related_name='price_history'
    )
    
    # Price data
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='JPY')
    original_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    
    # Availability
    is_available = models.BooleanField(default=True)
    stock_status = models.CharField(max_length=50, blank=True, default='')
    stock_quantity = models.IntegerField(null=True, blank=True)
    
    # Source
    source = models.CharField(max_length=20, default='CRAWLER')  # CRAWLER, API, MANUAL, IMPORT
    
    # Timing
    scraped_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.product_url_id}: {self.price} {self.currency} @ {self.scraped_at}"
