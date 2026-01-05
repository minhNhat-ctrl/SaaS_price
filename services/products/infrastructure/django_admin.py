"""
Django Admin Configuration

Based on PRODUCTS_DATA_CONTRACT.md architecture.
- Product, ProductURLMapping: Tenant models (registered here)
- Domain, ProductURL, PriceHistory: Shared models (registered in products_shared)
"""
from django.contrib import admin
from services.products.infrastructure.django_models import (
    Product,
    ProductURLMapping,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin interface for Product."""
    list_display = ['name', 'sku', 'gtin', 'status', 'tenant_id', 'created_at']
    list_filter = ['status']
    search_fields = ['name', 'sku', 'gtin']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'tenant_id', 'name', 'status')
        }),
        ('Identifiers', {
            'fields': ('sku', 'gtin')
        }),
        ('Additional Data', {
            'fields': ('custom_attributes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ProductURLMapping)
class ProductURLMappingAdmin(admin.ModelAdmin):
    """Admin interface for ProductURLMapping."""
    list_display = ['product', 'url_hash_short', 'is_primary', 'display_order', 'created_at']
    list_filter = ['is_primary']
    search_fields = ['url_hash', 'custom_label']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def url_hash_short(self, obj):
        """Display shortened URL hash."""
        return obj.url_hash[:16] + '...' if obj.url_hash else ''
    url_hash_short.short_description = 'URL Hash'
