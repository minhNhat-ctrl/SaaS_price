"""DTO contracts for Access module/application boundary."""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID


@dataclass
class MembershipInvitationCommand:
    tenant_id: UUID
    invitee_email: str
    role_slugs: List[str]
    invited_by: UUID
    expires_at: Optional[datetime] = None


@dataclass
class MembershipActivationCommand:
    tenant_id: UUID
    membership_id: UUID
    activated_by: UUID


@dataclass
class MembershipRevokeCommand:
    tenant_id: UUID
    membership_id: UUID
    revoked_by: UUID
    reason: Optional[str] = None


@dataclass
class PermissionCheckQuery:
    tenant_id: UUID
    user_id: UUID
    resource: str
    action: str
