"""
Access Service - Core Authorization & RBAC Use Cases

Business logic for managing memberships, roles, and permissions.
No Django dependencies - pure business logic.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from core.access.domain import (
    Membership,
    MembershipStatus,
    Role,
    RoleType,
    Permission,
    Policy,
    MembershipAlreadyExistsError,
    MembershipNotFoundError,
    RoleNotFoundError,
    PermissionDeniedError,
)
from core.access.repositories import (
    MembershipRepository,
    RoleRepository,
    PermissionRepository,
    PolicyRepository,
)


class AccessService:
    """
    Main service for access control operations.
    
    Responsibilities:
    - Membership management (invite, activate, revoke)
    - Role assignment and management
    - Permission checking
    - Policy evaluation
    """
    
    def __init__(
        self,
        membership_repo: MembershipRepository,
        role_repo: RoleRepository,
        permission_repo: PermissionRepository,
        policy_repo: PolicyRepository,
    ):
        self.membership_repo = membership_repo
        self.role_repo = role_repo
        self.permission_repo = permission_repo
        self.policy_repo = policy_repo
    
    # ============================================================
    # Membership Management
    # ============================================================
    
    async def invite_member(
        self,
        user_id: UUID,
        tenant_id: UUID,
        role_slugs: List[str],
        invited_by: UUID,
        expires_at: Optional[datetime] = None,
    ) -> Membership:
        """
        Invite user to tenant with specified roles.
        
        Args:
            user_id: User to invite
            tenant_id: Tenant to join
            role_slugs: List of role slugs to assign
            invited_by: User who sent invitation
            expires_at: Optional expiration date
        
        Returns:
            Membership entity
        
        Raises:
            MembershipAlreadyExistsError: If membership exists
            RoleNotFoundError: If role doesn't exist
        """
        # Check if membership already exists
        existing = await self.membership_repo.get_by_user_and_tenant(user_id, tenant_id)
        if existing:
            raise MembershipAlreadyExistsError(str(user_id), str(tenant_id))
        
        # Load roles
        roles = []
        for slug in role_slugs:
            role = await self.role_repo.get_by_slug(slug, tenant_id)
            if not role:
                raise RoleNotFoundError(slug)
            roles.append(role)
        
        # Create membership
        membership = Membership(
            id=UUID(int=0),  # Will be set by repository
            user_id=user_id,
            tenant_id=tenant_id,
            roles=roles,
            status=MembershipStatus.INVITED,
            invited_by=invited_by,
            expires_at=expires_at,
        )
        
        return await self.membership_repo.create(membership)
    
    async def invite_member_by_email(
        self,
        tenant_id: UUID,
        email: str,
        role_slugs: List[str],
        invited_by: UUID,
        expires_at: Optional[datetime] = None,
    ) -> Membership:
        """
        Invite member to tenant by email (không cần user_id trước).
        
        Flow:
        1. Kiểm tra xem email đã có user chưa
        2. Nếu chưa → tạo temporary user_id (UUID from email hash)
        3. Tạo membership với status INVITED
        4. Khi user đăng ký và xác nhận email → activate membership
        
        Args:
            tenant_id: Tenant to join
            email: Email to invite
            role_slugs: List of role slugs to assign
            invited_by: User who sent invitation
            expires_at: Optional expiration date
        
        Returns:
            Membership entity
        
        Raises:
            MembershipAlreadyExistsError: If membership exists for this email
            RoleNotFoundError: If role doesn't exist
        """
        from uuid import uuid5, NAMESPACE_DNS
        
        # Generate deterministic UUID from email (consistent across calls)
        user_id = uuid5(NAMESPACE_DNS, f"invite:{email}".lower())
        
        # Check if membership already exists for this email
        existing = await self.membership_repo.get_by_user_and_tenant(user_id, tenant_id)
        if existing:
            raise MembershipAlreadyExistsError(email, str(tenant_id))
        
        # Load roles
        roles = []
        for slug in role_slugs:
            role = await self.role_repo.get_by_slug(slug, tenant_id)
            if not role:
                raise RoleNotFoundError(slug)
            roles.append(role)
        
        # Create membership
        membership = Membership(
            id=UUID(int=0),  # Will be set by repository
            user_id=user_id,
            tenant_id=tenant_id,
            roles=roles,
            status=MembershipStatus.INVITED,
            invited_by=invited_by,
            expires_at=expires_at,
            metadata={'invited_email': email},  # Store email for reference
        )
        
        return await self.membership_repo.create(membership)
    
    async def activate_membership(self, membership_id: UUID) -> Membership:
        """
        Activate invited membership (user accepted invitation).
        
        Args:
            membership_id: Membership to activate
        
        Returns:
            Updated membership
        
        Raises:
            MembershipNotFoundError: If membership doesn't exist
        """
        membership = await self.membership_repo.get_by_id(membership_id)
        if not membership:
            raise MembershipNotFoundError("", "")
        
        membership.activate()
        return await self.membership_repo.update(membership)
    
    async def suspend_membership(self, membership_id: UUID) -> Membership:
        """
        Suspend membership (temporarily disable access).
        
        Args:
            membership_id: Membership to suspend
        
        Returns:
            Updated membership
        """
        membership = await self.membership_repo.get_by_id(membership_id)
        if not membership:
            raise MembershipNotFoundError("", "")
        
        membership.suspend()
        return await self.membership_repo.update(membership)
    
    async def revoke_membership(self, membership_id: UUID) -> bool:
        """
        Revoke membership (permanently remove access).
        
        Args:
            membership_id: Membership to revoke
        
        Returns:
            True if revoked successfully
        """
        return await self.membership_repo.delete(membership_id)
    
    async def get_user_memberships(self, user_id: UUID) -> List[Membership]:
        """Get all memberships for a user."""
        return await self.membership_repo.list_by_user(user_id)
    
    async def get_tenant_members(
        self, 
        tenant_id: UUID, 
        status: Optional[MembershipStatus] = None
    ) -> List[Membership]:
        """Get all members of a tenant."""
        return await self.membership_repo.list_by_tenant(tenant_id, status)
    
    # ============================================================
    # Role Management
    # ============================================================
    
    async def assign_role(self, membership_id: UUID, role_slug: str) -> Membership:
        """
        Assign role to membership.
        
        Args:
            membership_id: Membership to update
            role_slug: Role to assign
        
        Returns:
            Updated membership
        
        Raises:
            MembershipNotFoundError: If membership doesn't exist
            RoleNotFoundError: If role doesn't exist
        """
        membership = await self.membership_repo.get_by_id(membership_id)
        if not membership:
            raise MembershipNotFoundError("", "")
        
        role = await self.role_repo.get_by_slug(role_slug, membership.tenant_id)
        if not role:
            raise RoleNotFoundError(role_slug)
        
        membership.add_role(role)
        return await self.membership_repo.update(membership)
    
    async def revoke_role(self, membership_id: UUID, role_slug: str) -> Membership:
        """
        Revoke role from membership.
        
        Args:
            membership_id: Membership to update
            role_slug: Role to revoke
        
        Returns:
            Updated membership
        """
        membership = await self.membership_repo.get_by_id(membership_id)
        if not membership:
            raise MembershipNotFoundError("", "")
        
        role = await self.role_repo.get_by_slug(role_slug, membership.tenant_id)
        if role:
            membership.remove_role(role)
            return await self.membership_repo.update(membership)
        
        return membership
    
    async def create_role(
        self,
        name: str,
        slug: str,
        role_type: RoleType,
        permission_strings: List[str],
        tenant_id: Optional[UUID] = None,
        description: str = "",
        is_default: bool = False,
    ) -> Role:
        """
        Create new role with permissions.
        
        Args:
            name: Role display name
            slug: URL-safe identifier
            role_type: System, tenant, or custom
            permission_strings: List of permission strings (resource:action)
            tenant_id: Tenant ID (for tenant/custom roles)
            description: Role description
            is_default: Auto-assign to new members
        
        Returns:
            Created role
        """
        # Load permissions
        permissions = []
        for perm_str in permission_strings:
            perm = await self.permission_repo.get_by_string(perm_str)
            if not perm:
                # Create permission if it doesn't exist
                perm = Permission.from_string(perm_str)
                perm = await self.permission_repo.create(perm)
            permissions.append(perm)
        
        # Create role
        role = Role(
            id=UUID(int=0),  # Will be set by repository
            name=name,
            slug=slug,
            role_type=role_type,
            permissions=permissions,
            tenant_id=tenant_id,
            description=description,
            is_default=is_default,
        )
        
        return await self.role_repo.create(role)
    
    async def get_role(self, role_slug: str, tenant_id: Optional[UUID] = None) -> Optional[Role]:
        """Get role by slug."""
        return await self.role_repo.get_by_slug(role_slug, tenant_id)
    
    async def list_tenant_roles(self, tenant_id: UUID) -> List[Role]:
        """List all roles for a tenant."""
        return await self.role_repo.list_by_type(RoleType.TENANT, tenant_id)
    
    # ============================================================
    # Permission Checking
    # ============================================================
    
    async def check_permission(
        self,
        user_id: UUID,
        tenant_id: UUID,
        permission_string: str,
    ) -> bool:
        """
        Check if user has permission in tenant.
        
        Args:
            user_id: User to check
            tenant_id: Tenant context
            permission_string: Permission to check (resource:action)
        
        Returns:
            True if user has permission
        """
        membership = await self.membership_repo.get_by_user_and_tenant(user_id, tenant_id)
        if not membership or not membership.is_active():
            return False
        
        return membership.has_permission(permission_string)
    
    async def require_permission(
        self,
        user_id: UUID,
        tenant_id: UUID,
        permission_string: str,
    ):
        """
        Assert that user has permission (raises exception if not).
        
        Raises:
            PermissionDeniedError: If user doesn't have permission
        """
        has_perm = await self.check_permission(user_id, tenant_id, permission_string)
        if not has_perm:
            resource, action = permission_string.split(':', 1)
            raise PermissionDeniedError(str(user_id), resource, action)
    
    async def get_user_permissions(
        self,
        user_id: UUID,
        tenant_id: UUID,
    ) -> List[str]:
        """
        Get all permissions for user in tenant.
        
        Returns:
            List of permission strings
        """
        membership = await self.membership_repo.get_by_user_and_tenant(user_id, tenant_id)
        if not membership or not membership.is_active():
            return []
        
        return membership.get_all_permissions()
    
    # ============================================================
    # System Role Initialization
    # ============================================================
    
    async def initialize_system_roles(self):
        """
        Initialize default system roles.
        
        Called during platform setup to create:
        - super_admin: Full platform access
        - platform_support: Limited support access
        - tenant_admin: Full tenant access (template)
        - tenant_member: Basic tenant access (template)
        """
        system_roles = [
            {
                "name": "Super Admin",
                "slug": "super_admin",
                "role_type": RoleType.SYSTEM,
                "permissions": ["*:*"],  # Wildcard: all permissions
                "description": "Platform super administrator with full access",
            },
            {
                "name": "Platform Support",
                "slug": "platform_support",
                "role_type": RoleType.SYSTEM,
                "permissions": ["tenant:read", "user:read", "support:manage"],
                "description": "Platform support staff with read access",
            },
            {
                "name": "Tenant Admin",
                "slug": "tenant_admin",
                "role_type": RoleType.TENANT,
                "permissions": [
                    "tenant:read",
                    "tenant:write",
                    "user:invite",
                    "user:manage",
                    "billing:manage",
                    "settings:manage",
                ],
                "description": "Tenant administrator with full tenant access",
                "is_default": False,
            },
            {
                "name": "Tenant Member",
                "slug": "tenant_member",
                "role_type": RoleType.TENANT,
                "permissions": ["tenant:read", "content:read", "content:write"],
                "description": "Basic tenant member with read/write access",
                "is_default": True,
            },
        ]
        
        for role_data in system_roles:
            # Check if role already exists
            existing = await self.role_repo.get_by_slug(role_data["slug"])
            if not existing:
                await self.create_role(
                    name=role_data["name"],
                    slug=role_data["slug"],
                    role_type=role_data["role_type"],
                    permission_strings=role_data["permissions"],
                    description=role_data["description"],
                    is_default=role_data.get("is_default", False),
                )
