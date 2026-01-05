"""
Django Admin Configuration for Shared Products Data

Based on PRODUCTS_DATA_CONTRACT.md architecture.
Models in PUBLIC schema: Domain, ProductURL, PriceHistory
"""
from django.contrib import admin
from services.products_shared.infrastructure.django_models import (
    Domain,
    ProductURL,
    PriceHistory,
)


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    """Admin interface for Domain."""
    list_display = ['name', 'get_url_count', 'is_active', 'health_status', 'created_at']
    list_filter = ['is_active', 'health_status']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def get_url_count(self, obj):
        """Count URLs for this domain."""
        return obj.urls.count()
    get_url_count.short_description = 'URL Count'


@admin.register(ProductURL)
class ProductURLAdmin(admin.ModelAdmin):
    """Admin interface for ProductURL."""
    list_display = ['get_domain_name', 'url_hash_short', 'reference_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'domain']
    search_fields = ['raw_url', 'normalized_url', 'url_hash']
    readonly_fields = ['id', 'url_hash', 'normalized_url', 'created_at', 'updated_at']
    
    def get_domain_name(self, obj):
        """Get domain name."""
        return obj.domain.name if obj.domain else ''
    get_domain_name.short_description = 'Domain'
    
    def url_hash_short(self, obj):
        """Display shortened URL hash."""
        return obj.url_hash[:16] + '...' if obj.url_hash else ''
    url_hash_short.short_description = 'URL Hash'


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    """Admin interface for PriceHistory."""
    list_display = ['url_hash_short', 'price', 'currency', 'is_available', 'source', 'scraped_at']
    list_filter = ['currency', 'source', 'is_available']
    search_fields = ['url_hash']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'scraped_at'
    
    def url_hash_short(self, obj):
        """Display shortened URL hash."""
        return obj.url_hash[:16] + '...' if obj.url_hash else ''
    url_hash_short.short_description = 'URL Hash'
