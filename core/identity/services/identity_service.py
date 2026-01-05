"""
Identity Service - business use-cases for authentication/identity.

Principles:
- No Django imports
- No HTTP/session handling
- Delegates persistence/auth to repository
- No tenant, no role logic here
"""
import secrets
from typing import Optional
from uuid import UUID
import logging

from core.identity.domain.identity import UserIdentity, Credential, AuthToken, VerificationToken
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
    
    # ============================================================
    # Email Verification Flow
    # ============================================================
    
    async def request_email_verification(self, email: str) -> str:
        """
        Generate and send email verification link.
        Returns token for reference.
        """
        identity = await self.repository.get_by_email(email)
        if not identity:
            raise IdentityNotFoundError(email)
        
        if identity.email_verified:
            logger.info("Email already verified for email=%s", email)
            return "already_verified"
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        verification = VerificationToken.create_email_verification(email, token)
        
        # Store token
        await self.repository.create_verification_token(verification)
        
        # Send email
        await self.repository.send_verification_email(email, token, 'email_verify')
        logger.info("Email verification sent to email=%s", email)
        
        return token
    
    async def verify_email_token(self, token: str) -> UserIdentity:
        """
        Verify email using token.
        Returns verified user identity.
        """
        verification = await self.repository.get_verification_token(token)
        if not verification:
            raise InvalidCredentialError("Invalid or expired verification token")
        
        if verification.token_type != 'email_verify':
            raise InvalidCredentialError("Invalid token type")
        
        if verification.is_expired():
            await self.repository.delete_verification_token(token)
            raise InvalidCredentialError("Verification token has expired")
        
        # Mark email as verified
        await self.repository.mark_email_verified(verification.email)
        
        # Delete used token
        await self.repository.delete_verification_token(token)
        
        identity = await self.repository.get_by_email(verification.email)
        logger.info("Email verified for email=%s", verification.email)
        return identity
    
    # ============================================================
    # Password Reset Flow
    # ============================================================
    
    async def request_password_reset(self, email: str) -> str:
        """
        Generate and send password reset link.
        Returns token for reference.
        """
        identity = await self.repository.get_by_email(email)
        if not identity:
            # For security, don't reveal if email exists
            logger.warning("Password reset requested for non-existent email=%s", email)
            return "email_sent"  # Pretend we sent it
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        reset_token = VerificationToken.create_password_reset(email, token)
        
        # Store token
        await self.repository.create_verification_token(reset_token)
        
        # Send email
        await self.repository.send_verification_email(email, token, 'password_reset')
        logger.info("Password reset link sent to email=%s", email)
        
        return token
    
    async def reset_password_with_token(self, token: str, new_password: str) -> UserIdentity:
        """
        Reset password using token.
        Returns user identity.
        """
        verification = await self.repository.get_verification_token(token)
        if not verification:
            raise InvalidCredentialError("Invalid or expired reset token")
        
        if verification.token_type != 'password_reset':
            raise InvalidCredentialError("Invalid token type")
        
        if verification.is_expired():
            await self.repository.delete_verification_token(token)
            raise InvalidCredentialError("Reset token has expired")
        
        # Set new password
        await self.repository.set_password(verification.email, new_password)
        
        # Delete used token
        await self.repository.delete_verification_token(token)
        
        identity = await self.repository.get_by_email(verification.email)
        logger.info("Password reset successful for email=%s", verification.email)
        return identity
    
    # ============================================================
    # Magic Link Login Flow
    # ============================================================
    
    async def request_magic_link(self, email: str) -> str:
        """
        Generate and send magic link for passwordless login.
        Returns token for reference.
        """
        identity = await self.repository.get_by_email(email)
        if not identity:
            raise IdentityNotFoundError(email)
        
        if not identity.is_active:
            raise InvalidCredentialError("Account is not active")
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        magic_token = VerificationToken.create_magic_link(email, token)
        
        # Store token
        await self.repository.create_verification_token(magic_token)
        
        # Send email
        await self.repository.send_verification_email(email, token, 'magic_link')
        logger.info("Magic link sent to email=%s", email)
        
        return token
    
    async def authenticate_with_magic_link(self, token: str) -> AuthToken:
        """
        Authenticate user using magic link token.
        Returns auth token for session creation.
        """
        verification = await self.repository.get_verification_token(token)
        if not verification:
            raise InvalidCredentialError("Invalid or expired magic link")
        
        if verification.token_type != 'magic_link':
            raise InvalidCredentialError("Invalid token type")
        
        if verification.is_expired():
            await self.repository.delete_verification_token(token)
            raise InvalidCredentialError("Magic link has expired")
        
        identity = await self.repository.get_by_email(verification.email)
        if not identity:
            raise IdentityNotFoundError(verification.email)
        
        # Delete used token
        await self.repository.delete_verification_token(token)
        
        # Issue auth token
        auth_token = await self.repository.issue_token(identity)
        logger.info("Magic link login successful for email=%s", verification.email)
        
        return auth_token
