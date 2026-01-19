"""DTO helpers for Access API adapters."""

from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID


@dataclass(slots=True)
class InviteMemberRequestDTO:
    tenant_id: UUID
    email: str
    role_slugs: List[str]
    expires_at: Optional[str] = None


@dataclass(slots=True)
class UpdateMembershipStatusDTO:
    tenant_id: UUID
    membership_id: UUID
    status: str
