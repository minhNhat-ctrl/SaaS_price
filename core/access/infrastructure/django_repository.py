"""
Django ORM Implementation of Access Repositories

Concrete implementations using Django ORM.
⚠️ IMPORTANT: Access data is in PUBLIC schema (SHARED_APPS)
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from django_tenants.utils import get_public_schema_name, schema_context
from asgiref.sync import sync_to_async

from core.access.domain import (
    Membership,
    MembershipStatus,
    Role,
    RoleType,
    Permission,
    Policy,
)
from core.access.repositories.access_repo import (
    MembershipRepository,
    RoleRepository,
    PermissionRepository,
    PolicyRepository,
)
from core.access.infrastructure.django_models import (
    Membership as MembershipModel,
    Role as RoleModel,
    Permission as PermissionModel,
    Policy as PolicyModel,
)


class DjangoMembershipRepository(MembershipRepository):
    """Django ORM implementation of MembershipRepository."""
    
    def _membership_model_to_entity(self, model: MembershipModel) -> Membership:
        """Convert Django model to domain entity."""
        return Membership(
            id=model.id,
            user_id=model.user_id,
            tenant_id=model.tenant_id,
            status=MembershipStatus(model.status),
            roles=[
                Role(
                    id=r.id,
                    name=r.name,
                    slug=r.slug,
                    role_type=RoleType(r.role_type),
                    permissions=[],
                    description=r.description,
                    tenant_id=r.tenant_id,
                    is_default=r.is_default,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
                for r in model.roles.all()
            ],
            invited_by=model.invited_by,
            invited_at=model.invited_at,
            joined_at=model.joined_at,
            expires_at=model.expires_at,
            metadata=model.metadata or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    async def create(self, membership: Membership) -> Membership:
        """Create new membership in PUBLIC schema."""
        @sync_to_async
        def _create():
            with schema_context(get_public_schema_name()):
                model = MembershipModel.objects.create(
                    id=membership.id,
                    user_id=membership.user_id,
                    tenant_id=membership.tenant_id,
                    status=membership.status.value,
                    invited_by=membership.invited_by,
                    invited_at=membership.invited_at,
                    joined_at=membership.joined_at,
                    expires_at=membership.expires_at,
                    metadata=membership.metadata,
                )
                # Set M2M relationships
                if membership.roles:
                    role_ids = [r.id for r in membership.roles]
                    roles = RoleModel.objects.filter(id__in=role_ids)
                    model.roles.set(roles)
                model.refresh_from_db()
                return self._membership_model_to_entity(model)
        
        return await _create()
    
    async def get_by_id(self, membership_id: UUID) -> Optional[Membership]:
        """Get membership by ID from PUBLIC schema."""
        @sync_to_async
        def _get():
            with schema_context(get_public_schema_name()):
                try:
                    model = MembershipModel.objects.select_related().prefetch_related('roles').get(id=membership_id)
                    return self._membership_model_to_entity(model)
                except MembershipModel.DoesNotExist:
                    return None
        
        return await _get()
    
    async def get_by_user_and_tenant(self, user_id: UUID, tenant_id: UUID) -> Optional[Membership]:
        """Get membership by user and tenant from PUBLIC schema."""
        @sync_to_async
        def _get():
            with schema_context(get_public_schema_name()):
                try:
                    model = MembershipModel.objects.select_related().prefetch_related('roles').get(
                        user_id=user_id,
                        tenant_id=tenant_id
                    )
                    return self._membership_model_to_entity(model)
                except MembershipModel.DoesNotExist:
                    return None
        
        return await _get()
    
    async def list_by_user(self, user_id: UUID) -> List[Membership]:
        """List all memberships for a user from PUBLIC schema."""
        @sync_to_async
        def _list():
            with schema_context(get_public_schema_name()):
                models = MembershipModel.objects.filter(user_id=user_id).prefetch_related('roles')
                return [self._membership_model_to_entity(m) for m in models]
        
        return await _list()
    
    async def list_by_tenant(
        self, 
        tenant_id: UUID, 
        status: Optional[MembershipStatus] = None
    ) -> List[Membership]:
        """List all memberships for a tenant from PUBLIC schema."""
        @sync_to_async
        def _list():
            with schema_context(get_public_schema_name()):
                queryset = MembershipModel.objects.filter(tenant_id=tenant_id).prefetch_related('roles')
                if status:
                    queryset = queryset.filter(status=status.value)
                return [self._membership_model_to_entity(m) for m in queryset]
        
        return await _list()
    
    async def update(self, membership: Membership) -> Membership:
        """Update membership in PUBLIC schema."""
        @sync_to_async
        def _update():
            with schema_context(get_public_schema_name()):
                model = MembershipModel.objects.get(id=membership.id)
                model.status = membership.status.value
                model.invited_by = membership.invited_by
                model.invited_at = membership.invited_at
                model.joined_at = membership.joined_at
                model.expires_at = membership.expires_at
                model.metadata = membership.metadata
                model.save()
                
                # Update M2M relationships
                if membership.roles:
                    role_ids = [r.id for r in membership.roles]
                    roles = RoleModel.objects.filter(id__in=role_ids)
                    model.roles.set(roles)
                
                model.refresh_from_db()
                return self._membership_model_to_entity(model)
        
        return await _update()
    
    async def delete(self, membership_id: UUID) -> bool:
        """Delete membership from PUBLIC schema."""
        @sync_to_async
        def _delete():
            with schema_context(get_public_schema_name()):
                try:
                    MembershipModel.objects.filter(id=membership_id).delete()
                    return True
                except Exception:
                    return False
        
        return await _delete()


class DjangoRoleRepository(RoleRepository):
    """Django ORM implementation of RoleRepository (Stub)."""
    
    async def create(self, role: Role) -> Role:
        """Create new role."""
        # Stub: return as-is
        return role
    
    async def get_by_id(self, role_id: UUID) -> Optional[Role]:
        """Get role by ID."""
        # Stub: return None
        return None
    
    async def get_by_slug(self, slug: str, tenant_id: Optional[UUID] = None) -> Optional[Role]:
        """
        Get role by slug (optionally scoped to tenant).
        ⚠️ MUST query from PUBLIC schema!
        """
        @sync_to_async
        def _get():
            with schema_context(get_public_schema_name()):
                try:
                    role_model = RoleModel.objects.get(slug=slug, tenant_id=tenant_id)
                    # Convert Django model to domain entity
                    return Role(
                        id=role_model.id,
                        name=role_model.name,
                        slug=role_model.slug,
                        role_type=RoleType(role_model.role_type),
                        permissions=[],  # TODO: load permissions
                        description=role_model.description,
                        tenant_id=role_model.tenant_id,
                        is_default=role_model.is_default,
                        created_at=role_model.created_at,
                        updated_at=role_model.updated_at,
                    )
                except RoleModel.DoesNotExist:
                    return None
        
        return await _get()
    
    async def list_by_type(
        self, 
        role_type: RoleType, 
        tenant_id: Optional[UUID] = None
    ) -> List[Role]:
        """List roles by type."""
        # Stub: return empty list
        return []
    
    async def list_default_roles(self, tenant_id: Optional[UUID] = None) -> List[Role]:
        """List default roles (auto-assigned to new members)."""
        # Stub: return empty list
        return []
    
    async def update(self, role: Role) -> Role:
        """Update role."""
        # Stub: return as-is
        return role
    
    async def delete(self, role_id: UUID) -> bool:
        """Delete role."""
        # Stub: return success
        return True


class DjangoPermissionRepository(PermissionRepository):
    """Django ORM implementation of PermissionRepository (Stub)."""
    
    async def create(self, permission: Permission) -> Permission:
        """Create new permission."""
        # Stub: return as-is
        return permission
    
    async def get_by_id(self, permission_id: UUID) -> Optional[Permission]:
        """Get permission by ID."""
        # Stub: return None
        return None
    
    async def get_by_string(self, permission_string: str) -> Optional[Permission]:
        """Get permission by string format (resource:action)."""
        # Stub: return None
        return None
    
    async def list_all(self) -> List[Permission]:
        """List all permissions."""
        # Stub: return empty list
        return []
    
    async def list_by_resource(self, resource: str) -> List[Permission]:
        """List permissions for a specific resource."""
        # Stub: return empty list
        return []
    
    async def delete(self, permission_id: UUID) -> bool:
        """Delete permission."""
        # Stub: return success
        return True


class DjangoPolicyRepository(PolicyRepository):
    """Django ORM implementation of PolicyRepository (Stub)."""
    
    async def create(self, policy: Policy) -> Policy:
        """Create new policy."""
        # Stub: return as-is
        return policy
    
    async def get_by_id(self, policy_id: UUID) -> Optional[Policy]:
        """Get policy by ID."""
        # Stub: return None
        return None
    
    async def list_active(self, tenant_id: Optional[UUID] = None) -> List[Policy]:
        """List active policies."""
        # Stub: return empty list
        return []
    
    async def update(self, policy: Policy) -> Policy:
        """Update policy."""
        # Stub: return as-is
        return policy
    
    async def delete(self, policy_id: UUID) -> bool:
        """Delete policy."""
        # Stub: return success
        return True
