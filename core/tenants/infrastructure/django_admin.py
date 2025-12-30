"""
Django Admin Configuration cho Tenant Module

Mục đích:
- Cấu hình interface admin để manage tenants
- Auto-load mà không cần import trực tiếp
- Tuân thủ nguyên tắc kiến trúc (infrastructure layer)

Auto-load via apps.py ready() method
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count

from .django_models import Tenant, TenantDomain


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """
    Admin interface cho Tenant model
    
    Features:
    - List view: Hiển thị tenant với status, domains count
    - Search: Tìm kiếm theo name, slug, domain
    - Filter: Lọc theo status
    - Readonly fields: id, created_at, updated_at
    - Fieldsets: Tổ chức hiển thị
    """

    list_display = [
        'name',
        'slug_display',
        'status_badge',
        'domains_count',
        'created_at',
    ]

    list_filter = [
        'status',
        'created_at',
        'updated_at',
    ]

    search_fields = [
        'name',
        'slug',
        'domains__domain',
    ]

    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'domains_list',
    ]

    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'name', 'slug', 'status')
        }),
        ('Domains', {
            'fields': ('domains_list',),
            'description': 'Manage domains via Tenant Domain admin'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def slug_display(self, obj):
        """Hiển thị slug (có thể highlight)"""
        return format_html(
            '<code style="background-color: #f0f0f0; padding: 2px 5px;">{}</code>',
            obj.slug
        )
    slug_display.short_description = 'Slug'

    def status_badge(self, obj):
        """
        Hiển thị status dưới dạng badge màu
        - Active: green
        - Suspended: orange
        - Deleted: red
        """
        colors = {
            'active': '#28a745',
            'suspended': '#ffc107',
            'deleted': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def domains_count(self, obj):
        """Hiển thị số lượng domains"""
        count = obj.domains.count()
        return format_html(
            '<span style="background-color: #e9ecef; padding: 2px 6px; border-radius: 3px;">{} domain(s)</span>',
            count
        )
    domains_count.short_description = 'Domains'

    def domains_list(self, obj):
        """Hiển thị danh sách domains (readonly)"""
        domains = obj.domains.all()
        if not domains:
            return "No domains configured"
        
        html = '<ul style="list-style-type: none; padding: 0;">'
        for domain in domains:
            badge = '⭐ PRIMARY' if domain.is_primary else 'secondary'
            html += f'<li><code>{domain.domain}</code> <small>({badge})</small></li>'
        html += '</ul>'
        
        return format_html(html)
    domains_list.short_description = 'Domains'

    actions = [
        'make_active',
        'make_suspended',
    ]

    def make_active(self, request, queryset):
        """Action: Activate tenants"""
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} tenant(s) activated')
    make_active.short_description = '✓ Mark selected as Active'

    def make_suspended(self, request, queryset):
        """Action: Suspend tenants"""
        updated = queryset.update(status='suspended')
        self.message_user(request, f'{updated} tenant(s) suspended')
    make_suspended.short_description = '⏸ Mark selected as Suspended'

    def get_queryset(self, request):
        """Optimize query với select_related và prefetch_related"""
        queryset = super().get_queryset(request)
        # Prefetch domains khi list
        return queryset.prefetch_related('domains')

    class Media:
        """CSS/JS thêm cho admin"""
        css = {
            'all': ('css/tenant_admin.css',)
        }


@admin.register(TenantDomain)
class TenantDomainAdmin(admin.ModelAdmin):
    """
    Admin interface cho TenantDomain model
    
    Features:
    - Inline editing
    - Link to tenant
    - Search by domain
    """

    list_display = [
        'domain',
        'tenant_link',
        'is_primary_badge',
    ]

    list_filter = [
        'is_primary',
        'tenant__status',
    ]

    search_fields = [
        'domain',
        'tenant__name',
        'tenant__slug',
    ]

    readonly_fields = [
        'tenant_link',
    ]

    fieldsets = (
        ('Domain Info', {
            'fields': ('domain', 'is_primary', 'tenant')
        }),
        ('Tenant Reference', {
            'fields': ('tenant_link',),
            'classes': ('collapse',)
        }),
    )

    def tenant_link(self, obj):
        """Link sang tenant admin"""
        if obj.tenant:
            url = reverse('admin:platform_tenants_tenant_change', args=[obj.tenant.id])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.tenant.name
            )
        return '-'
    tenant_link.short_description = 'Tenant'

    def is_primary_badge(self, obj):
        """Hiển thị primary status"""
        if obj.is_primary:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">⭐ PRIMARY</span>'
            )
        return format_html(
            '<span style="color: #6c757d;">secondary</span>'
        )
    is_primary_badge.short_description = 'Primary'

    def get_queryset(self, request):
        """Optimize query"""
        queryset = super().get_queryset(request)
        return queryset.select_related('tenant')


# Custom admin site (optional)
class TenantAdminSite(admin.AdminSite):
    """
    Custom AdminSite cho Tenant module (optional)
    
    Có thể dùng để:
    - Customize branding
    - Add custom views
    - Custom permission checks
    
    Để dùng: từ main urls.py
    from core.tenants.infrastructure.django_admin import tenant_admin_site
    urlpatterns = [
        path('admin/', tenant_admin_site.urls),
    ]
    """
    site_header = "SaaS Platform - Tenant Management"
    site_title = "Tenant Admin"
    index_title = "Welcome to Tenant Management"

    def each_context(self, request):
        """Add custom context"""
        context = super().each_context(request)
        # Add stats
        context['total_tenants'] = Tenant.objects.count()
        context['active_tenants'] = Tenant.objects.filter(status='active').count()
        context['suspended_tenants'] = Tenant.objects.filter(status='suspended').count()
        return context


# Instantiate custom admin site (optional)
tenant_admin_site = TenantAdminSite(name='tenant_admin')
tenant_admin_site.register(Tenant, TenantAdmin)
tenant_admin_site.register(TenantDomain, TenantDomainAdmin)
