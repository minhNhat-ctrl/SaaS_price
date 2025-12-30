"""
Django Admin Configuration for Access Module

Admin interface for managing memberships, roles, permissions, and policies.
"""
from django.contrib import admin
from django.utils.html import format_html

from .django_models import Membership, Role, Permission, Policy


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin interface for Permission model."""
    
    list_display = [
        'permission_string_display',
        'resource',
        'action',
        'created_at',
    ]
    
    list_filter = [
        'resource',
        'action',
    ]
    
    search_fields = [
        'resource',
        'action',
        'description',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
    ]
    
    fieldsets = (
        ('Permission Details', {
            'fields': ('id', 'resource', 'action', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def permission_string_display(self, obj):
        """Display permission as colored badge."""
        return format_html(
            '<code style="background-color: #e9ecef; padding: 2px 6px; border-radius: 3px;">{}</code>',
            obj.permission_string
        )
    permission_string_display.short_description = 'Permission'


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin interface for Role model."""
    
    list_display = [
        'name',
        'slug',
        'role_type_badge',
        'permissions_count',
        'is_default',
        'created_at',
    ]
    
    list_filter = [
        'role_type',
        'is_default',
        'created_at',
    ]
    
    search_fields = [
        'name',
        'slug',
        'description',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'permissions_list',
    ]
    
    filter_horizontal = ['permissions']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'name', 'slug', 'role_type', 'description')
        }),
        ('Scope', {
            'fields': ('tenant_id', 'is_default')
        }),
        ('Permissions', {
            'fields': ('permissions', 'permissions_list'),
            'description': 'Assign permissions to this role'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def role_type_badge(self, obj):
        """Display role type as colored badge."""
        colors = {
            'system': '#dc3545',
            'tenant': '#28a745',
            'custom': '#17a2b8',
        }
        color = colors.get(obj.role_type, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_role_type_display()
        )
    role_type_badge.short_description = 'Type'
    
    def permissions_count(self, obj):
        """Display permissions count."""
        count = obj.permissions.count()
        return format_html(
            '<span style="background-color: #e9ecef; padding: 2px 6px; border-radius: 3px;">{} permission(s)</span>',
            count
        )
    permissions_count.short_description = 'Permissions'
    
    def permissions_list(self, obj):
        """Display permissions list (readonly)."""
        permissions = obj.permissions.all()
        if not permissions:
            return "No permissions assigned"
        
        html = '<ul style="list-style-type: none; padding: 0;">'
        for perm in permissions:
            html += f'<li><code>{perm.permission_string}</code> - {perm.description}</li>'
        html += '</ul>'
        
        return format_html(html)
    permissions_list.short_description = 'Assigned Permissions'


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Admin interface for Membership model."""
    
    list_display = [
        'user_id',
        'tenant_id',
        'status_badge',
        'roles_count',
        'invited_at',
        'joined_at',
    ]
    
    list_filter = [
        'status',
        'invited_at',
        'joined_at',
    ]
    
    search_fields = [
        'user_id',
        'tenant_id',
    ]
    
    readonly_fields = [
        'id',
        'invited_at',
        'created_at',
        'updated_at',
        'roles_list',
    ]
    
    filter_horizontal = ['roles']
    
    fieldsets = (
        ('Membership Info', {
            'fields': ('id', 'user_id', 'tenant_id', 'status')
        }),
        ('Invitation', {
            'fields': ('invited_by', 'invited_at', 'joined_at', 'expires_at')
        }),
        ('Roles', {
            'fields': ('roles', 'roles_list'),
            'description': 'Assign roles to this membership'
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'active': '#28a745',
            'suspended': '#ffc107',
            'invited': '#17a2b8',
            'expired': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def roles_count(self, obj):
        """Display roles count."""
        count = obj.roles.count()
        return format_html(
            '<span style="background-color: #e9ecef; padding: 2px 6px; border-radius: 3px;">{} role(s)</span>',
            count
        )
    roles_count.short_description = 'Roles'
    
    def roles_list(self, obj):
        """Display roles list (readonly)."""
        roles = obj.roles.all()
        if not roles:
            return "No roles assigned"
        
        html = '<ul style="list-style-type: none; padding: 0;">'
        for role in roles:
            html += f'<li><strong>{role.name}</strong> ({role.slug})</li>'
        html += '</ul>'
        
        return format_html(html)
    roles_list.short_description = 'Assigned Roles'
    
    actions = [
        'activate_memberships',
        'suspend_memberships',
    ]
    
    def activate_memberships(self, request, queryset):
        """Action: Activate memberships."""
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} membership(s) activated')
    activate_memberships.short_description = '✓ Activate selected memberships'
    
    def suspend_memberships(self, request, queryset):
        """Action: Suspend memberships."""
        updated = queryset.update(status='suspended')
        self.message_user(request, f'{updated} membership(s) suspended')
    suspend_memberships.short_description = '⏸ Suspend selected memberships'


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    """Admin interface for Policy model."""
    
    list_display = [
        'name',
        'policy_type',
        'is_active',
        'tenant_id',
        'created_at',
    ]
    
    list_filter = [
        'policy_type',
        'is_active',
        'created_at',
    ]
    
    search_fields = [
        'name',
        'description',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Policy Info', {
            'fields': ('id', 'name', 'description', 'policy_type')
        }),
        ('Scope', {
            'fields': ('tenant_id', 'is_active')
        }),
        ('Rules', {
            'fields': ('rules',),
            'description': 'Policy rules in JSON format'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'activate_policies',
        'deactivate_policies',
    ]
    
    def activate_policies(self, request, queryset):
        """Action: Activate policies."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} policy(ies) activated')
    activate_policies.short_description = '✓ Activate selected policies'
    
    def deactivate_policies(self, request, queryset):
        """Action: Deactivate policies."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} policy(ies) deactivated')
    deactivate_policies.short_description = '⏸ Deactivate selected policies'
