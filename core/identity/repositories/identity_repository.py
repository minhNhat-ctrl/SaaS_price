"""
Repository interface for Identity module.

Rules:
- Define abstract operations only
- No Django imports
- Concrete implementations live in infrastructure/
"""
from typing import Protocol, Optional
from uuid import UUID

from core.identity.domain.identity import UserIdentity, Credential, AuthToken


class IdentityRepository(Protocol):
    async def get_by_id(self, user_id: UUID) -> Optional[UserIdentity]:
        ...

    async def get_by_email(self, email: str) -> Optional[UserIdentity]:
        ...

    async def create_user(self, identity: UserIdentity, password: str) -> UserIdentity:
        ...

    async def set_password(self, email: str, new_password: str) -> None:
        ...

    async def verify_password(self, credential: Credential) -> bool:
        ...

    async def mark_email_verified(self, email: str) -> None:
        ...

    async def issue_token(self, identity: UserIdentity) -> AuthToken:
        ...

    async def revoke_tokens(self, user_id: UUID) -> None:
        ...
