"""
Domain Entities for Access Module

Pure business logic - no Django dependencies.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4


class MembershipStatus(Enum):
    """Membership status enumeration."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INVITED = "invited"
    EXPIRED = "expired"


class RoleType(Enum):
    """Role type classification."""
    SYSTEM = "system"  # Platform-wide roles (e.g., super_admin)
    TENANT = "tenant"  # Tenant-specific roles (e.g., tenant_admin, member)
    CUSTOM = "custom"  # User-defined custom roles


@dataclass
class Permission:
    """
    Permission entity - represents a specific action on a resource.
    
    Format: <resource>:<action>
    Examples:
    - tenant:read
    - tenant:write
    - user:invite
    - billing:manage
    """
    id: UUID
    resource: str  # e.g., 'tenant', 'user', 'billing'
    action: str    # e.g., 'read', 'write', 'delete', 'manage'
    description: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate permission format."""
        if not self.resource or not self.action:
            raise ValueError("Permission resource and action are required")
    
    @property
    def permission_string(self) -> str:
        """Return permission in string format: resource:action"""
        return f"{self.resource}:{self.action}"
    
    @staticmethod
    def from_string(permission_str: str, permission_id: UUID = None, description: str = "") -> 'Permission':
        """Create Permission from string format (resource:action)."""
        if ':' not in permission_str:
            raise ValueError(f"Invalid permission format: {permission_str}")
        
        resource, action = permission_str.split(':', 1)
        return Permission(
            id=permission_id or uuid4(),
            resource=resource.strip(),
            action=action.strip(),
            description=description
        )


@dataclass
class Role:
    """
    Role entity - collection of permissions.
    
    Roles can be:
    - System roles: Platform-wide (super_admin, platform_support)
    - Tenant roles: Tenant-specific (tenant_admin, tenant_member)
    - Custom roles: User-defined per tenant
    """
    id: UUID
    name: str
    slug: str  # URL-safe identifier
    role_type: RoleType
    permissions: List[Permission] = field(default_factory=list)
    description: str = ""
    tenant_id: Optional[UUID] = None  # None for system roles
    is_default: bool = False  # Auto-assign to new members
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_permission(self, permission: Permission):
        """Add permission to role."""
        if permission not in self.permissions:
            self.permissions.append(permission)
            self.updated_at = datetime.utcnow()
    
    def remove_permission(self, permission: Permission):
        """Remove permission from role."""
        if permission in self.permissions:
            self.permissions.remove(permission)
            self.updated_at = datetime.utcnow()
    
    def has_permission(self, permission_string: str) -> bool:
        """Check if role has specific permission."""
        return any(p.permission_string == permission_string for p in self.permissions)
    
    def get_permission_strings(self) -> List[str]:
        """Get all permissions as string list."""
        return [p.permission_string for p in self.permissions]


@dataclass
class Membership:
    """
    Membership entity - represents user-tenant relationship with roles.
    
    A user can have multiple memberships (one per tenant).
    Each membership has one or more roles within that tenant.
    """
    id: UUID
    user_id: UUID  # Reference to user (from identity module)
    tenant_id: UUID  # Reference to tenant
    roles: List[Role] = field(default_factory=list)
    status: MembershipStatus = MembershipStatus.INVITED
    invited_by: Optional[UUID] = None
    invited_at: datetime = field(default_factory=datetime.utcnow)
    joined_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def activate(self):
        """Activate membership."""
        self.status = MembershipStatus.ACTIVE
        self.joined_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def suspend(self):
        """Suspend membership."""
        self.status = MembershipStatus.SUSPENDED
        self.updated_at = datetime.utcnow()
    
    def is_active(self) -> bool:
        """Check if membership is active."""
        if self.status != MembershipStatus.ACTIVE:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True
    
    def add_role(self, role: Role):
        """Add role to membership."""
        if role not in self.roles:
            self.roles.append(role)
            self.updated_at = datetime.utcnow()
    
    def remove_role(self, role: Role):
        """Remove role from membership."""
        if role in self.roles:
            self.roles.remove(role)
            self.updated_at = datetime.utcnow()
    
    def has_role(self, role_slug: str) -> bool:
        """Check if membership has specific role."""
        return any(r.slug == role_slug for r in self.roles)
    
    def get_all_permissions(self) -> List[str]:
        """Get all permissions from all roles."""
        permissions = set()
        for role in self.roles:
            permissions.update(role.get_permission_strings())
        return list(permissions)
    
    def has_permission(self, permission_string: str) -> bool:
        """Check if membership has specific permission through any role."""
        return permission_string in self.get_all_permissions()


@dataclass
class Policy:
    """
    Policy entity - defines authorization rules.
    
    Policies can be:
    - Attribute-based (ABAC): Based on user/resource attributes
    - Time-based: Valid during specific time windows
    - Context-based: Based on request context (IP, device, etc.)
    """
    id: UUID
    name: str
    description: str
    policy_type: str  # 'abac', 'time_based', 'context_based'
    rules: Dict[str, Any]  # JSON-like policy rules
    tenant_id: Optional[UUID] = None  # None for system-wide policies
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate policy against context.
        
        This is a placeholder - actual implementation would use
        a policy engine (e.g., OPA, Casbin).
        """
        # TODO: Implement policy evaluation logic
        return True
