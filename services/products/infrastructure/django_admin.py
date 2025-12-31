"""
Django Admin for Products Module

Rich admin interface following module self-registration pattern.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg, Min, Max
from services.products.infrastructure.django_models import (
    TenantProduct,
    SharedProduct,
    SharedProductURL,
    SharedPriceHistory,
)


@admin.register(TenantProduct)
class TenantProductAdmin(admin.ModelAdmin):
    """Admin interface for Tenant Products."""
    
    list_display = [
        'name_with_status',
        'sku',
        'tenant_id_short',
        'status_badge',
        'brand',
        'category',
        'shared_link',
        'created_at',
    ]
    list_filter = ['status', 'brand', 'category', 'is_public', 'created_at']
    search_fields = ['name', 'sku', 'barcode', 'gtin', 'internal_code', 'tenant_id']
    readonly_fields = ['id', 'tenant_id', 'created_at', 'updated_at', 'custom_attributes_display']
    
    fieldsets = [
        ('Identification', {
            'fields': ['id', 'tenant_id', 'status']
        }),
        ('Basic Information', {
            'fields': ['name', 'internal_code', 'sku', 'barcode', 'qr_code', 'gtin']
        }),
        ('Classification', {
            'fields': ['brand', 'category']
        }),
        ('Shared Product Link', {
            'fields': ['shared_product_id'],
            'description': 'Link to canonical shared product'
        }),
        ('Custom Attributes', {
            'fields': ['custom_attributes', 'custom_attributes_display'],
            'classes': ['collapse']
        }),
        ('Settings', {
            'fields': ['is_public']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    actions = ['activate_products', 'archive_products']
    
    def name_with_status(self, obj):
        """Product name with status icon."""
        icons = {
            'ACTIVE': '✓',
            'DRAFT': '📝',
            'ARCHIVED': '📦',
            'DISCONTINUED': '🚫'
        }
        icon = icons.get(obj.status, '')
        return format_html('<strong>{}</strong> {}', icon, obj.name)
    name_with_status.short_description = 'Product'
    
    def tenant_id_short(self, obj):
        """Short tenant ID."""
        return format_html('<code>{}</code>', str(obj.tenant_id)[:8])
    tenant_id_short.short_description = 'Tenant'
    
    def status_badge(self, obj):
        """Status badge."""
        colors = {
            'ACTIVE': '#4caf50',
            'DRAFT': '#ff9800',
            'ARCHIVED': '#757575',
            'DISCONTINUED': '#f44336',
        }
        color = colors.get(obj.status, '#999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    
    def shared_link(self, obj):
        """Shared product link indicator."""
        if obj.shared_product_id:
            return format_html('<span style="color: #1976d2;">🔗 Linked</span>')
        return format_html('<span style="color: #999;">-</span>')
    shared_link.short_description = 'Shared'
    
    def custom_attributes_display(self, obj):
        """Display custom attributes as formatted JSON."""
        import json
        if obj.custom_attributes:
            formatted = json.dumps(obj.custom_attributes, indent=2)
            return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>', formatted)
        return 'No custom attributes'
    custom_attributes_display.short_description = 'Custom Attributes (Read-only)'
    
    def activate_products(self, request, queryset):
        """Bulk activate products."""
        updated = queryset.update(status='ACTIVE')
        self.message_user(request, f'{updated} products activated.')
    activate_products.short_description = 'Activate selected products'
    
    def archive_products(self, request, queryset):
        """Bulk archive products."""
        updated = queryset.update(status='ARCHIVED')
        self.message_user(request, f'{updated} products archived.')
    archive_products.short_description = 'Archive selected products'


@admin.register(SharedProduct)
class SharedProductAdmin(admin.ModelAdmin):
    """Admin interface for Shared Products."""
    
    list_display = [
        'normalized_name_display',
        'gtin',
        'manufacturer',
        'url_count',
        'created_at',
    ]
    list_filter = ['manufacturer', 'created_at']
    search_fields = ['gtin', 'ean', 'upc', 'manufacturer', 'normalized_name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'specs_hash']
    
    fieldsets = [
        ('Identification', {
            'fields': ['id', 'gtin', 'ean', 'upc']
        }),
        ('Product Info', {
            'fields': ['manufacturer', 'normalized_name']
        }),
        ('Deduplication', {
            'fields': ['specs_hash'],
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def normalized_name_display(self, obj):
        """Product name display."""
        return format_html('<strong>{}</strong>', obj.normalized_name or obj.gtin)
    normalized_name_display.short_description = 'Product'
    
    def url_count(self, obj):
        """Count of associated URLs."""
        # This would need a proper query in production
        return format_html('<span style="color: #1976d2;">📎 URLs</span>')
    url_count.short_description = 'URLs'


@admin.register(SharedProductURL)
class SharedProductURLAdmin(admin.ModelAdmin):
    """Admin interface for Product URLs."""
    
    list_display = [
        'domain_with_icon',
        'product_id_short',
        'marketplace_badge',
        'currency',
        'is_active_icon',
        'price_count',
        'created_at',
    ]
    list_filter = ['marketplace_type', 'is_active', 'currency', 'domain', 'created_at']
    search_fields = ['domain', 'full_url', 'product_id']
    readonly_fields = ['id', 'product_id', 'created_at', 'updated_at', 'full_url_display', 'meta_display']
    
    fieldsets = [
        ('Identification', {
            'fields': ['id', 'product_id']
        }),
        ('URL Information', {
            'fields': ['domain', 'full_url', 'full_url_display', 'marketplace_type']
        }),
        ('Price Settings', {
            'fields': ['currency', 'is_active']
        }),
        ('Metadata', {
            'fields': ['meta', 'meta_display'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    actions = ['activate_urls', 'deactivate_urls']
    
    def domain_with_icon(self, obj):
        """Domain with marketplace icon."""
        icons = {
            'AMAZON': '🛒',
            'RAKUTEN': '🏪',
            'SHOPEE': '🛍️',
            'LAZADA': '📦',
            'MANUFACTURER': '🏭',
            'CUSTOM': '🌐',
        }
        icon = icons.get(obj.marketplace_type, '🌐')
        return format_html('{} <strong>{}</strong>', icon, obj.domain)
    domain_with_icon.short_description = 'Domain'
    
    def product_id_short(self, obj):
        """Short product ID."""
        return format_html('<code>{}</code>', str(obj.product_id)[:8])
    product_id_short.short_description = 'Product'
    
    def marketplace_badge(self, obj):
        """Marketplace badge."""
        colors = {
            'AMAZON': '#ff9900',
            'RAKUTEN': '#bf0000',
            'SHOPEE': '#ee4d2d',
            'LAZADA': '#0f146d',
            'MANUFACTURER': '#1976d2',
            'CUSTOM': '#757575',
        }
        color = colors.get(obj.marketplace_type, '#999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.marketplace_type
        )
    marketplace_badge.short_description = 'Marketplace'
    
    def is_active_icon(self, obj):
        """Active status icon."""
        if obj.is_active:
            return format_html('<span style="color: #4caf50;">●</span>')
        return format_html('<span style="color: #f44336;">●</span>')
    is_active_icon.short_description = 'Active'
    
    def price_count(self, obj):
        """Price records count."""
        return format_html('<span style="color: #1976d2;">💰 Prices</span>')
    price_count.short_description = 'Prices'
    
    def full_url_display(self, obj):
        """Display full URL as clickable link."""
        if obj.full_url:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.full_url, obj.full_url[:100])
        return '-'
    full_url_display.short_description = 'Full URL'
    
    def meta_display(self, obj):
        """Display metadata as formatted JSON."""
        import json
        if obj.meta:
            formatted = json.dumps(obj.meta, indent=2)
            return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>', formatted)
        return 'No metadata'
    meta_display.short_description = 'Metadata (Read-only)'
    
    def activate_urls(self, request, queryset):
        """Bulk activate URLs."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} URLs activated.')
    activate_urls.short_description = 'Activate selected URLs'
    
    def deactivate_urls(self, request, queryset):
        """Bulk deactivate URLs."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} URLs deactivated.')
    deactivate_urls.short_description = 'Deactivate selected URLs'


@admin.register(SharedPriceHistory)
class SharedPriceHistoryAdmin(admin.ModelAdmin):
    """Admin interface for Price History."""
    
    list_display = [
        'price_display',
        'product_url_id_short',
        'currency',
        'source_badge',
        'recorded_at',
    ]
    list_filter = ['currency', 'source', 'recorded_at']
    search_fields = ['product_url_id']
    readonly_fields = ['id', 'product_url_id', 'recorded_at', 'meta_display']
    date_hierarchy = 'recorded_at'
    
    fieldsets = [
        ('Identification', {
            'fields': ['id', 'product_url_id']
        }),
        ('Price Data', {
            'fields': ['price', 'currency', 'source']
        }),
        ('Timestamp', {
            'fields': ['recorded_at']
        }),
        ('Metadata', {
            'fields': ['meta', 'meta_display'],
            'classes': ['collapse']
        }),
    ]
    
    def price_display(self, obj):
        """Price with currency symbol."""
        symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'JPY': '¥',
        }
        symbol = symbols.get(obj.currency, obj.currency)
        return format_html('<strong style="font-size: 14px; color: #1976d2;">{}{}</strong>', symbol, obj.price)
    price_display.short_description = 'Price'
    
    def product_url_id_short(self, obj):
        """Short product URL ID."""
        return format_html('<code>{}</code>', str(obj.product_url_id)[:8])
    product_url_id_short.short_description = 'Product URL'
    
    def source_badge(self, obj):
        """Source badge."""
        colors = {
            'CRAWLER': '#4caf50',
            'API': '#2196f3',
            'MANUAL': '#ff9800',
            'IMPORT': '#9c27b0',
        }
        color = colors.get(obj.source, '#999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.source
        )
    source_badge.short_description = 'Source'
    
    def meta_display(self, obj):
        """Display metadata as formatted JSON."""
        import json
        if obj.meta:
            formatted = json.dumps(obj.meta, indent=2)
            return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>', formatted)
        return 'No metadata'
    meta_display.short_description = 'Metadata (Read-only)'
