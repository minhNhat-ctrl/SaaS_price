"""
Django Admin for Products Module

Rich admin interface following module self-registration pattern.
Provides comprehensive product data management for admin-core module.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg, Min, Max, Q
from django.urls import path
from django.shortcuts import render
from django.db import connection
from datetime import datetime, timedelta
from services.products.infrastructure.django_models import (
    TenantProduct,
    SharedProduct,
    SharedProductURL,
    SharedPriceHistory,
    TenantProductURLTracking,
)


# ============================================================
# Admin Site Customization (Sidebar Links)
# ============================================================

class ProductsAdminSiteMixin:
    """Mixin để thêm sidebar links cho products module."""
    
    def index(self, request, extra_context=None):
        """Override index để thêm products module links."""
        extra_context = extra_context or {}
        
        extra_context['products_module_links'] = [
            {
                'name': '📦 Shared Products',
                'url': '/admin/secure-admin-2025/products/sharedproduct/',
                'description': 'Canonical products across all tenants'
            },
            {
                'name': '🔗 Product URLs',
                'url': '/admin/secure-admin-2025/products/sharedproducturl/',
                'description': 'Marketplace & website URLs'
            },
            {
                'name': '💰 Price History',
                'url': '/admin/secure-admin-2025/products/sharedpricehistory/',
                'description': 'Time-series price tracking'
            },
        ]
        
        return super().index(request, extra_context)


# ============================================================
# Inline Admins for Related Data
# ============================================================

class SharedProductURLInline(admin.TabularInline):
    """Inline display of product URLs within SharedProduct detail."""
    model = SharedProductURL
    extra = 0
    readonly_fields = ['id', 'domain', 'created_at']
    fields = ['domain', 'marketplace_type', 'currency', 'is_active', 'created_at']
    can_delete = False


class SharedPriceHistoryInline(admin.TabularInline):
    """
    Inline display of recent prices within SharedProductURL detail.
    
    ❌ DISABLED: SharedPriceHistory doesn't have ForeignKey to SharedProductURL
    (has product_url_id as UUID field instead)
    Use custom display method (price_history_display) instead.
    """
    model = SharedPriceHistory
    extra = 0
    readonly_fields = ['id', 'price', 'currency', 'source', 'recorded_at']
    fields = ['price', 'currency', 'source', 'recorded_at']
    can_delete = False
    ordering = ['-recorded_at']
    
    # def get_queryset(self, request):
    #     """Show only last 10 price records."""
    #     qs = super().get_queryset(request)
    #     return qs[:10]


class TenantProductURLTrackingInline(admin.TabularInline):
    """Inline display of URL tracking within TenantProduct detail."""
    model = TenantProductURLTracking
    extra = 0
    readonly_fields = ['id', 'shared_url_id', 'created_at']
    fields = ['shared_url_id', 'custom_label', 'is_primary', 'created_at']
    can_delete = False


# ============================================================
# Custom Admin Actions & Filters
# ============================================================

class ActiveProductFilter(admin.SimpleListFilter):
    """Filter by product active status."""
    title = 'Active Status'
    parameter_name = 'active'
    
    def lookups(self, request, model_admin):
        return (
            ('active', 'Active'),
            ('inactive', 'Inactive'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(status='ACTIVE')
        if self.value() == 'inactive':
            return queryset.exclude(status='ACTIVE')


class PriceSourceFilter(admin.SimpleListFilter):
    """Filter price history by source."""
    title = 'Price Source'
    parameter_name = 'price_source'
    
    def lookups(self, request, model_admin):
        return (
            ('CRAWLER', 'Web Crawler'),
            ('API', 'API'),
            ('MANUAL', 'Manual Entry'),
            ('IMPORT', 'Bulk Import'),
        )
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(source=self.value())



# ❌ TenantProduct is NOT registered here
# Reason: TenantProduct is a TENANT model (lives in tenant schema, not public schema)
# Admin-core runs on public schema, so it cannot see tenant models
# TenantProduct should only be managed via API or within tenant context

class TenantProductAdmin(admin.ModelAdmin):
    """
    Admin interface for Tenant Products (NOT REGISTERED - tenant-only model).
    
    ❗ NOTE: This class is kept for reference only.
    TenantProduct cannot be registered in admin because:
    - It lives in TENANT schema
    - Admin-core runs in PUBLIC schema
    - Schema mismatch → "Not available for this type of schema"
    
    Management via:
    - API: POST /api/products/
    - Tenant context: requires switching to tenant schema
    
    Features (if enabled in tenant context):
    - Rich product information display
    - URL tracking inline view
    - Bulk actions for status management
    - Comprehensive filtering and search
    - Product statistics
    """
    
    list_display = [
        'name_with_status',
        'sku',
        'tenant_id_short',
        'status_badge',
        'brand',
        'category',
        'shared_link',
        'url_tracking_count',
        'created_at',
    ]
    list_filter = [
        'status',
        'brand',
        'category',
        'is_public',
        ActiveProductFilter,
        'created_at',
    ]
    search_fields = [
        'name',
        'sku',
        'barcode',
        'gtin',
        'internal_code',
        'tenant_id',
        'category',
        'brand',
    ]
    readonly_fields = [
        'id',
        'tenant_id',
        'created_at',
        'updated_at',
        'custom_attributes_display',
        'linked_urls_count',
        'stats_display',
    ]
    inlines = [TenantProductURLTrackingInline]
    
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
        ('Tracking & URLs', {
            'fields': ['linked_urls_count', 'stats_display'],
            'description': 'URL tracking information'
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
    
    def url_tracking_count(self, obj):
        """Count of URL trackings for this product."""
        from services.products.infrastructure.django_models import TenantProductURLTracking
        count = TenantProductURLTracking.objects.filter(product_id=obj.id).count()
        if count > 0:
            return format_html('<span style="color: #1976d2;">📎 {}</span>', count)
        return format_html('<span style="color: #999;">-</span>')
    url_tracking_count.short_description = 'Tracked URLs'
    
    def linked_urls_count(self, obj):
        """Display count of linked URLs."""
        from services.products.infrastructure.django_models import TenantProductURLTracking
        count = TenantProductURLTracking.objects.filter(product_id=obj.id).count()
        return format_html(
            '<span style="background: #f5f5f5; padding: 8px; border-radius: 4px; display: inline-block;">'
            '<strong>Tracked URLs:</strong> {} 🔗'
            '</span>',
            count
        )
    linked_urls_count.short_description = 'URL Tracking'
    
    def stats_display(self, obj):
        """Display product statistics."""
        from services.products.infrastructure.django_models import TenantProductURLTracking
        
        tracking_count = TenantProductURLTracking.objects.filter(product_id=obj.id).count()
        
        stats_html = (
            '<div style="background: #f9f9f9; padding: 12px; border-radius: 4px; border-left: 4px solid #1976d2;">'
            '<strong>Product Statistics:</strong><br>'
            f'<strong>Tracked URLs:</strong> {tracking_count}<br>'
            f'<strong>Status:</strong> {obj.status}<br>'
            f'<strong>Visibility:</strong> {"Public" if obj.is_public else "Private"}<br>'
            f'<strong>Created:</strong> {obj.created_at.strftime("%Y-%m-%d %H:%M")}<br>'
            '</div>'
        )
        return format_html(stats_html)
    stats_display.short_description = 'Statistics'



class SharedProductAdmin(admin.ModelAdmin):
    """
    Admin interface for Shared Products (Canonical Products).
    
    Features:
    - Displays normalized product data
    - Shows linked product URLs inline
    - Deduplication tracking (specs_hash)
    - URL count display
    - Price statistics
    """
    
    list_display = [
        'normalized_name_display',
        'gtin_display',
        'manufacturer_display',
        'url_count',
        'latest_price_display',
        'created_at',
    ]
    list_filter = [
        'manufacturer',
        'created_at',
    ]
    search_fields = [
        'gtin',
        'ean',
        'upc',
        'manufacturer',
        'normalized_name',
    ]
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'specs_hash',
        'urls_summary',
        'price_stats',
    ]
    inlines = [SharedProductURLInline]
    
    fieldsets = [
        ('Identification', {
            'fields': ['id', 'gtin', 'ean', 'upc']
        }),
        ('Product Info', {
            'fields': ['manufacturer', 'normalized_name']
        }),
        ('URL Summary', {
            'fields': ['urls_summary'],
        }),
        ('Price Statistics', {
            'fields': ['price_stats'],
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
    
    def gtin_display(self, obj):
        """GTIN display with code formatting."""
        return format_html('<code>{}</code>', obj.gtin)
    gtin_display.short_description = 'GTIN'
    
    def manufacturer_display(self, obj):
        """Manufacturer display."""
        if obj.manufacturer:
            return format_html('<span style="color: #666;">{}</span>', obj.manufacturer)
        return '-'
    manufacturer_display.short_description = 'Manufacturer'
    
    def url_count(self, obj):
        """Count of associated URLs with link indicator."""
        count = SharedProductURL.objects.filter(product_id=obj.id).count()
        if count > 0:
            return format_html(
                '<span style="background: #e3f2fd; padding: 4px 8px; border-radius: 3px; color: #1976d2;">'
                '📎 {}</span>',
                count
            )
        return format_html('<span style="color: #999;">-</span>')
    url_count.short_description = 'URLs'
    
    def latest_price_display(self, obj):
        """Show latest price for this product."""
        from services.products.infrastructure.django_models import SharedProductURL
        
        urls = SharedProductURL.objects.filter(
            product_id=obj.id,
            is_active=True
        ).order_by('-updated_at')[:1]
        
        if urls.exists():
            url = urls[0]
            latest_price = SharedPriceHistory.objects.filter(
                product_url_id=url.id
            ).order_by('-recorded_at').first()
            
            if latest_price:
                symbols = {'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥'}
                symbol = symbols.get(latest_price.currency, latest_price.currency)
                return format_html(
                    '<span style="color: #2e7d32; font-weight: bold;">{}{}</span>',
                    symbol, latest_price.price
                )
        return '-'
    latest_price_display.short_description = 'Latest Price'
    
    def urls_summary(self, obj):
        """Display summary of linked URLs."""
        urls = SharedProductURL.objects.filter(product_id=obj.id).values(
            'marketplace_type', 'currency', 'is_active'
        ).annotate(count=Count('id'))
        
        if not urls.exists():
            return '<span style="color: #999;">No URLs linked</span>'
        
        html = (
            '<div style="background: #f9f9f9; padding: 12px; border-radius: 4px; border-left: 4px solid #1976d2;">'
            '<strong>📎 URL Summary:</strong><br>'
        )
        
        for url_info in urls:
            status = '✓ Active' if url_info['is_active'] else '● Inactive'
            html += (
                f"{url_info['marketplace_type']} | {url_info['currency']} | {status}<br>"
            )
        
        html += '</div>'
        return format_html(html)
    urls_summary.short_description = 'URLs Summary'
    
    def price_stats(self, obj):
        """Display price statistics for all URLs."""
        from django.db.models import Min, Max, Avg
        from services.products.infrastructure.django_models import SharedProductURL
        
        urls = SharedProductURL.objects.filter(product_id=obj.id).values_list('id', flat=True)
        
        if not urls.exists():
            return '<span style="color: #999;">No price data available</span>'
        
        price_stats = SharedPriceHistory.objects.filter(
            product_url_id__in=urls
        ).aggregate(
            min_price=Min('price'),
            max_price=Max('price'),
            avg_price=Avg('price'),
            count=Count('id')
        )
        
        if price_stats['count'] == 0:
            return '<span style="color: #999;">No price data available</span>'
        
        html = (
            '<div style="background: #f9f9f9; padding: 12px; border-radius: 4px; border-left: 4px solid #4caf50;">'
            '<strong>💰 Price Statistics:</strong><br>'
            f"<strong>Total Records:</strong> {price_stats['count']}<br>"
            f"<strong>Min Price:</strong> ${price_stats['min_price']}<br>"
            f"<strong>Max Price:</strong> ${price_stats['max_price']}<br>"
            f"<strong>Avg Price:</strong> ${price_stats['avg_price']:.2f}<br>"
            '</div>'
        )
        return format_html(html)
    price_stats.short_description = 'Price Statistics'


@admin.register(SharedProduct)
class SharedProductAdminRegistered(SharedProductAdmin):
    """Registration wrapper for SharedProductAdmin"""
    pass


@admin.register(SharedProductURL)
class SharedProductURLAdmin(admin.ModelAdmin):
    """
    Admin interface for Product URLs.
    
    Features:
    - URL marketplace and domain display
    - Active status management
    - Price history inline view
    - Bulk activation/deactivation
    - Comprehensive URL filtering
    """
    
    list_display = [
        'domain_with_icon',
        'product_id_short',
        'marketplace_badge',
        'currency',
        'is_active_icon',
        'price_count',
        'last_price_display',
        'created_at',
    ]
    list_filter = [
        'marketplace_type',
        'is_active',
        'currency',
        'domain',
        'created_at',
    ]
    search_fields = [
        'domain',
        'full_url',
        'product_id',
    ]
    readonly_fields = [
        'id',
        'product_id',
        'created_at',
        'updated_at',
        'full_url_display',
        'meta_display',
        'price_trend_display',
        'price_history_display',
    ]
    # ❌ Removed: inlines = [SharedPriceHistoryInline]
    # Reason: SharedPriceHistory has no FK to SharedProductURL (uses product_url_id UUID)
    
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
        ('Price History', {
            'fields': ['price_history_display'],
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
    
    def price_history_display(self, obj):
        """Display recent price history records (readonly)."""
        prices = SharedPriceHistory.objects.filter(
            product_url_id=obj.id
        ).order_by('-recorded_at')[:5]  # Last 5 records
        
        if not prices.exists():
            return '<span style="color: #999;">No price records</span>'
        
        html = (
            '<div style="background: #f9f9f9; padding: 12px; border-radius: 4px; border-left: 4px solid #ff9800;">'
            '<strong>📈 Recent Price History (Last 5):</strong><br>'
            '<table style="width: 100%; margin-top: 8px; font-size: 12px;">'
            '<tr style="border-bottom: 1px solid #ddd;">'
            '<th style="padding: 4px; text-align: left;">Price</th>'
            '<th style="padding: 4px; text-align: left;">Source</th>'
            '<th style="padding: 4px; text-align: left;">Recorded</th>'
            '</tr>'
        )
        
        symbols = {'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥'}
        
        for price in prices:
            symbol = symbols.get(price.currency, price.currency)
            recorded_time = price.recorded_at.strftime('%Y-%m-%d %H:%M')
            html += (
                f'<tr style="border-bottom: 1px solid #eee;">'
                f'<td style="padding: 4px;"><strong>{symbol}{price.price}</strong></td>'
                f'<td style="padding: 4px;">{price.source}</td>'
                f'<td style="padding: 4px;">{recorded_time}</td>'
                f'</tr>'
            )
        
        html += (
            '</table>'
            f'<a href="/admin/secure-admin-2025/products/sharedpricehistory/?product_url_id={obj.id}" '
            'style="margin-top: 8px; display: inline-block; color: #1976d2; text-decoration: none;">View all prices →</a>'
            '</div>'
        )
        return format_html(html)
    price_history_display.short_description = 'Price History (Read-only)'
    
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
    
    def price_count(self, obj):
        """Price records count with link indicator."""
        count = SharedPriceHistory.objects.filter(product_url_id=obj.id).count()
        if count > 0:
            return format_html(
                '<span style="background: #fff3e0; padding: 4px 8px; border-radius: 3px; color: #e65100;">'
                '💰 {}</span>',
                count
            )
        return format_html('<span style="color: #999;">-</span>')
    price_count.short_description = 'Prices'
    
    def last_price_display(self, obj):
        """Display the most recent price."""
        latest = SharedPriceHistory.objects.filter(
            product_url_id=obj.id
        ).order_by('-recorded_at').first()
        
        if latest:
            symbols = {'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥'}
            symbol = symbols.get(latest.currency, latest.currency)
            time_ago = (datetime.now() - latest.recorded_at.replace(tzinfo=None)).days
            return format_html(
                '<span style="color: #2e7d32;">{}{}</span> <span style="color: #999; font-size: 11px;">{}d ago</span>',
                symbol, latest.price, time_ago
            )
        return '-'
    last_price_display.short_description = 'Last Price'
    
    def price_trend_display(self, obj):
        """Display price trend over time."""
        prices = SharedPriceHistory.objects.filter(
            product_url_id=obj.id
        ).order_by('-recorded_at')[:30]  # Last 30 records
        
        if prices.count() < 2:
            return '<span style="color: #999;">Insufficient data for trend</span>'
        
        prices_list = list(prices.values_list('price', 'recorded_at').order_by('recorded_at'))
        
        oldest_price = float(prices_list[0][0])
        latest_price = float(prices_list[-1][0])
        
        change = latest_price - oldest_price
        change_pct = (change / oldest_price * 100) if oldest_price > 0 else 0
        change_color = '#4caf50' if change <= 0 else '#f44336'
        change_arrow = '↓' if change <= 0 else '↑'
        
        symbols = {'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥'}
        symbol = symbols.get(obj.currency, obj.currency)
        
        html = (
            '<div style="background: #f9f9f9; padding: 12px; border-radius: 4px; border-left: 4px solid ' + change_color + ';">'
            f'<strong>📈 Price Trend (Last 30 records):</strong><br>'
            f'<strong>Oldest:</strong> {symbol}{oldest_price}<br>'
            f'<strong>Latest:</strong> {symbol}{latest_price}<br>'
            f'<span style="color: {change_color}; font-weight: bold;">{change_arrow} {abs(change):.2f} ({abs(change_pct):.1f}%)</span>'
            '</div>'
        )
        return format_html(html)
    price_trend_display.short_description = 'Price Trend'


@admin.register(SharedPriceHistory)
class SharedPriceHistoryAdmin(admin.ModelAdmin):
    """
    Admin interface for Price History - Time-series price tracking.
    
    Features:
    - Time-based hierarchical navigation (date_hierarchy)
    - Rich price display with formatting
    - Source tracking (Crawler, API, Manual, Import)
    - Efficient time-range queries
    - Recent price filtering
    """
    
    list_display = [
        'price_display',
        'product_url_id_short',
        'currency',
        'source_badge',
        'recorded_at',
        'age_display',
    ]
    list_filter = [
        'currency',
        'source',
        PriceSourceFilter,
        'recorded_at',
    ]
    search_fields = [
        'product_url_id',
    ]
    readonly_fields = [
        'id',
        'product_url_id',
        'recorded_at',
        'meta_display',
    ]
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
    def age_display(self, obj):
        """Display how long ago this price was recorded."""
        age = datetime.now() - obj.recorded_at.replace(tzinfo=None)
        if age.days == 0:
            return format_html('<span style="color: #4caf50;">Today</span>')
        elif age.days == 1:
            return format_html('<span style="color: #ff9800;">Yesterday</span>')
        else:
            return format_html('<span style="color: #999;">{}d ago</span>', age.days)
    age_display.short_description = 'Age'