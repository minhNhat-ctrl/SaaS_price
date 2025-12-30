"""
Django Models for Access Module

Django ORM implementation mapping domain entities to database tables.
"""
from django.db import models
import uuid


class Permission(models.Model):
    """
    Permission model - represents actions on resources.
    
    Format: resource:action (e.g., tenant:read, user:write)
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    resource = models.CharField(
        max_length=100,
        help_text="Resource type (e.g., tenant, user, billing)"
    )
    
    action = models.CharField(
        max_length=100,
        help_text="Action (e.g., read, write, delete, manage)"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Permission description"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "access_permissions"
        unique_together = [['resource', 'action']]
        indexes = [
            models.Index(fields=['resource']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.resource}:{self.action}"
    
    @property
    def permission_string(self):
        """Return permission as string."""
        return f"{self.resource}:{self.action}"


class Role(models.Model):
    """
    Role model - collection of permissions.
    
    Roles can be:
    - system: Platform-wide roles
    - tenant: Tenant-specific roles
    - custom: User-defined roles per tenant
    """
    ROLE_TYPE_CHOICES = [
        ('system', 'System'),
        ('tenant', 'Tenant'),
        ('custom', 'Custom'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    name = models.CharField(
        max_length=255,
        help_text="Role display name"
    )
    
    slug = models.SlugField(
        max_length=100,
        help_text="URL-safe identifier"
    )
    
    role_type = models.CharField(
        max_length=20,
        choices=ROLE_TYPE_CHOICES,
        default='tenant'
    )
    
    permissions = models.ManyToManyField(
        Permission,
        related_name='roles',
        blank=True
    )
    
    description = models.TextField(
        blank=True,
        help_text="Role description"
    )
    
    tenant_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Tenant ID (null for system roles)"
    )
    
    is_default = models.BooleanField(
        default=False,
        help_text="Auto-assign to new members"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "access_roles"
        unique_together = [['slug', 'tenant_id']]
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['role_type']),
            models.Index(fields=['tenant_id']),
            models.Index(fields=['is_default']),
        ]
    
    def __str__(self):
        return self.name


class Membership(models.Model):
    """
    Membership model - user-tenant relationship with roles.
    
    Represents a user's access to a specific tenant.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('invited', 'Invited'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    user_id = models.UUIDField(
        help_text="User ID (from identity module)"
    )
    
    tenant_id = models.UUIDField(
        help_text="Tenant ID"
    )
    
    roles = models.ManyToManyField(
        Role,
        related_name='memberships',
        help_text="Roles assigned to this membership"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='invited'
    )
    
    invited_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User who sent invitation"
    )
    
    invited_at = models.DateTimeField(auto_now_add=True)
    
    joined_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user accepted invitation"
    )
    
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Membership expiration date"
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata (JSON)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "access_memberships"
        unique_together = [['user_id', 'tenant_id']]
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['tenant_id']),
            models.Index(fields=['status']),
            models.Index(fields=['invited_at']),
        ]
    
    def __str__(self):
        return f"Membership {self.user_id} → {self.tenant_id}"


class Policy(models.Model):
    """
    Policy model - authorization rules.
    
    Policies define additional authorization logic beyond roles/permissions.
    """
    POLICY_TYPE_CHOICES = [
        ('abac', 'Attribute-Based'),
        ('time_based', 'Time-Based'),
        ('context_based', 'Context-Based'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    name = models.CharField(
        max_length=255,
        help_text="Policy name"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Policy description"
    )
    
    policy_type = models.CharField(
        max_length=50,
        choices=POLICY_TYPE_CHOICES,
        default='abac'
    )
    
    rules = models.JSONField(
        default=dict,
        help_text="Policy rules (JSON format)"
    )
    
    tenant_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Tenant ID (null for system-wide policies)"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether policy is active"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "access_policies"
        indexes = [
            models.Index(fields=['policy_type']),
            models.Index(fields=['tenant_id']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
