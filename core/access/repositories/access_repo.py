"""
Repository Interfaces for Access Module

Abstract interfaces for data access - no implementation details.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from core.access.domain import (
    Membership,
    MembershipStatus,
    Role,
    RoleType,
    Permission,
    Policy,
)


class MembershipRepository(ABC):
    """Repository interface for Membership operations."""
    
    @abstractmethod
    async def create(self, membership: Membership) -> Membership:
        """Create new membership."""
        pass
    
    @abstractmethod
    async def get_by_id(self, membership_id: UUID) -> Optional[Membership]:
        """Get membership by ID."""
        pass
    
    @abstractmethod
    async def get_by_user_and_tenant(self, user_id: UUID, tenant_id: UUID) -> Optional[Membership]:
        """Get membership by user and tenant."""
        pass
    
    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> List[Membership]:
        """List all memberships for a user."""
        pass
    
    @abstractmethod
    async def list_by_tenant(
        self, 
        tenant_id: UUID, 
        status: Optional[MembershipStatus] = None
    ) -> List[Membership]:
        """List all memberships for a tenant."""
        pass
    
    @abstractmethod
    async def update(self, membership: Membership) -> Membership:
        """Update membership."""
        pass
    
    @abstractmethod
    async def delete(self, membership_id: UUID) -> bool:
        """Delete membership."""
        pass


class RoleRepository(ABC):
    """Repository interface for Role operations."""
    
    @abstractmethod
    async def create(self, role: Role) -> Role:
        """Create new role."""
        pass
    
    @abstractmethod
    async def get_by_id(self, role_id: UUID) -> Optional[Role]:
        """Get role by ID."""
        pass
    
    @abstractmethod
    async def get_by_slug(self, slug: str, tenant_id: Optional[UUID] = None) -> Optional[Role]:
        """Get role by slug (optionally scoped to tenant)."""
        pass
    
    @abstractmethod
    async def list_by_type(
        self, 
        role_type: RoleType, 
        tenant_id: Optional[UUID] = None
    ) -> List[Role]:
        """List roles by type."""
        pass
    
    @abstractmethod
    async def list_default_roles(self, tenant_id: Optional[UUID] = None) -> List[Role]:
        """List default roles (auto-assigned to new members)."""
        pass
    
    @abstractmethod
    async def update(self, role: Role) -> Role:
        """Update role."""
        pass
    
    @abstractmethod
    async def delete(self, role_id: UUID) -> bool:
        """Delete role."""
        pass


class PermissionRepository(ABC):
    """Repository interface for Permission operations."""
    
    @abstractmethod
    async def create(self, permission: Permission) -> Permission:
        """Create new permission."""
        pass
    
    @abstractmethod
    async def get_by_id(self, permission_id: UUID) -> Optional[Permission]:
        """Get permission by ID."""
        pass
    
    @abstractmethod
    async def get_by_string(self, permission_string: str) -> Optional[Permission]:
        """Get permission by string format (resource:action)."""
        pass
    
    @abstractmethod
    async def list_all(self) -> List[Permission]:
        """List all permissions."""
        pass
    
    @abstractmethod
    async def list_by_resource(self, resource: str) -> List[Permission]:
        """List permissions for a specific resource."""
        pass
    
    @abstractmethod
    async def delete(self, permission_id: UUID) -> bool:
        """Delete permission."""
        pass


class PolicyRepository(ABC):
    """Repository interface for Policy operations."""
    
    @abstractmethod
    async def create(self, policy: Policy) -> Policy:
        """Create new policy."""
        pass
    
    @abstractmethod
    async def get_by_id(self, policy_id: UUID) -> Optional[Policy]:
        """Get policy by ID."""
        pass
    
    @abstractmethod
    async def list_active(self, tenant_id: Optional[UUID] = None) -> List[Policy]:
        """List active policies."""
        pass
    
    @abstractmethod
    async def update(self, policy: Policy) -> Policy:
        """Update policy."""
        pass
    
    @abstractmethod
    async def delete(self, policy_id: UUID) -> bool:
        """Delete policy."""
        pass
