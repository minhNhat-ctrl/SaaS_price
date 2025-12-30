"""
Identity Service - business use-cases for authentication/identity.

Principles:
- No Django imports
- No HTTP/session handling
- Delegates persistence/auth to repository
- No tenant, no role logic here
"""
from typing import Optional
from uuid import UUID
import logging

from core.identity.domain.identity import UserIdentity, Credential, AuthToken
from core.identity.domain.exceptions import (
    IdentityAlreadyExistsError,
    IdentityNotFoundError,
    InvalidCredentialError,
)
from core.identity.repositories import IdentityRepository

logger = logging.getLogger(__name__)


class IdentityService:
    def __init__(self, repository: IdentityRepository):
        self.repository = repository

    async def register_user(self, email: str, password: str, email_verified: bool = False) -> UserIdentity:
        existing = await self.repository.get_by_email(email)
        if existing:
            raise IdentityAlreadyExistsError(email)

        identity = UserIdentity.create(email=email, email_verified=email_verified)
        saved = await self.repository.create_user(identity, password)
        logger.info("Identity created for email=%s", email)
        return saved

    async def authenticate(self, email: str, password: str) -> AuthToken:
        cred = Credential(email=email, password=password)
        is_valid = await self.repository.verify_password(cred)
        if not is_valid:
            raise InvalidCredentialError("Invalid email or password")

        identity = await self.repository.get_by_email(email)
        if not identity:
            raise IdentityNotFoundError(email)

        token = await self.repository.issue_token(identity)
        logger.info("Issued token for email=%s", email)
        return token

    async def change_password(self, email: str, new_password: str) -> None:
        identity = await self.repository.get_by_email(email)
        if not identity:
            raise IdentityNotFoundError(email)
        await self.repository.set_password(email, new_password)
        logger.info("Password changed for email=%s", email)

    async def verify_email(self, email: str) -> None:
        identity = await self.repository.get_by_email(email)
        if not identity:
            raise IdentityNotFoundError(email)
        await self.repository.mark_email_verified(email)
        logger.info("Email verified for email=%s", email)

    async def revoke_sessions(self, user_id: UUID) -> None:
        await self.repository.revoke_tokens(user_id)
        logger.info("Revoked tokens for user_id=%s", user_id)
