"""
Django-allauth based repository implementation for Identity module.

Responsibilities:
- Map Django/allauth models to domain entities
- Handle password hashing & verification
- Issue logical tokens (stateless token generator)
- Handle email verification & magic links

Constraints:
- No tenant, no role logic
- Acts as adapter; services stay framework-agnostic
"""
import secrets
from typing import Optional
from uuid import UUID
from datetime import datetime

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from allauth.account.models import EmailAddress

from core.identity.domain.identity import UserIdentity, Credential, AuthToken, VerificationToken
from core.identity.domain.exceptions import IdentityNotFoundError
from core.identity.repositories import IdentityRepository

User = get_user_model()


def _user_to_domain(user: User) -> UserIdentity:
    email_verified = False
    try:
        email_obj = EmailAddress.objects.get(user=user, email=user.email)
        email_verified = email_obj.verified
    except EmailAddress.DoesNotExist:
        email_verified = False

    return UserIdentity(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        email_verified=email_verified,
    )


class DjangoAllauthIdentityRepository(IdentityRepository):
    async def get_by_id(self, user_id: UUID) -> Optional[UserIdentity]:
        @sync_to_async
        def _get():
            try:
                user = User.objects.get(id=user_id)
                # Get email verification status
                email_verified = False
                try:
                    email_obj = EmailAddress.objects.get(user=user, email=user.email)
                    email_verified = email_obj.verified
                except EmailAddress.DoesNotExist:
                    pass
                
                return UserIdentity(
                    id=user.id,
                    email=user.email,
                    is_active=user.is_active,
                    email_verified=email_verified,
                )
            except User.DoesNotExist:
                return None

        return await _get()

    async def get_by_email(self, email: str) -> Optional[UserIdentity]:
        @sync_to_async
        def _get():
            try:
                user = User.objects.get(email=email)
                # Get email verification status
                email_verified = False
                try:
                    email_obj = EmailAddress.objects.get(user=user, email=user.email)
                    email_verified = email_obj.verified
                except EmailAddress.DoesNotExist:
                    pass
                
                return UserIdentity(
                    id=user.id,
                    email=user.email,
                    is_active=user.is_active,
                    email_verified=email_verified,
                )
            except User.DoesNotExist:
                return None

        return await _get()

    async def create_user(self, identity: UserIdentity, password: str) -> UserIdentity:
        @sync_to_async
        def _create():
            # Use email as username for simplicity
            user = User.objects.create_user(
                username=identity.email,  # Use email as username
                email=identity.email,
                password=password,
                is_active=identity.is_active,
            )
            EmailAddress.objects.update_or_create(
                user=user,
                email=identity.email,
                defaults={"verified": identity.email_verified, "primary": True},
            )
            
            return UserIdentity(
                id=user.id,
                email=user.email,
                is_active=user.is_active,
                email_verified=identity.email_verified,
            )

        return await _create()

    async def set_password(self, email: str, new_password: str) -> None:
        @sync_to_async
        def _set():
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save(update_fields=["password"])

        await _set()

    async def verify_password(self, credential: Credential) -> bool:
        @sync_to_async
        def _auth():
            # Django's authenticate uses username by default
            # Since we're using email as username, authenticate with username=email
            user = authenticate(username=credential.email, password=credential.password)
            return user is not None

        return await _auth()

    async def mark_email_verified(self, email: str) -> None:
        @sync_to_async
        def _verify():
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise IdentityNotFoundError(email)

            EmailAddress.objects.update_or_create(
                user=user,
                email=email,
                defaults={"verified": True, "primary": True},
            )

        await _verify()

    async def issue_token(self, identity: UserIdentity) -> AuthToken:
        @sync_to_async
        def _token():
            try:
                user = User.objects.get(id=identity.id)
            except User.DoesNotExist:
                raise IdentityNotFoundError(identity.email)
            # Use Django's default token generator (stateless) as logical token
            token_str = default_token_generator.make_token(user)
            return AuthToken(token=token_str, user_id=user.id)

        return await _token()

    async def revoke_tokens(self, user_id: UUID) -> None:
        # Stateless token generator cannot revoke; rely on rotation/blacklist handled elsewhere.
        # Placeholder for future implementation (e.g., JWT blacklist).
        return None
    
    # ============================================================
    # Email Verification & Magic Link Implementation
    # ============================================================
    
    async def create_verification_token(self, token: VerificationToken) -> None:
        """Store verification token in cache (Redis/memory)."""
        @sync_to_async
        def _store():
            # Store in cache with expiration matching token expiry
            cache_key = f"verify_token:{token.token}"
            ttl_seconds = int((token.expires_at - datetime.utcnow()).total_seconds())
            cache.set(cache_key, {
                'email': token.email,
                'token_type': token.token_type,
                'expires_at': token.expires_at.isoformat(),
            }, timeout=max(ttl_seconds, 60))  # Min 60 seconds
        
        await _store()
    
    async def get_verification_token(self, token: str) -> Optional[VerificationToken]:
        """Retrieve verification token from cache."""
        @sync_to_async
        def _get():
            cache_key = f"verify_token:{token}"
            data = cache.get(cache_key)
            if not data:
                return None
            
            return VerificationToken(
                token=token,
                email=data['email'],
                expires_at=datetime.fromisoformat(data['expires_at']),
                token_type=data['token_type'],
            )
        
        return await _get()
    
    async def delete_verification_token(self, token: str) -> None:
        """Delete verification token after use."""
        @sync_to_async
        def _delete():
            cache_key = f"verify_token:{token}"
            cache.delete(cache_key)
        
        await _delete()
    
    async def send_verification_email(self, email: str, token: str, token_type: str) -> None:
        """Send verification email based on token type."""
        @sync_to_async
        def _send():
            # Build verification URL (adjust domain as needed)
            base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            
            if token_type == 'email_verify':
                verify_url = f"{base_url}/verify-email?token={token}"
                subject = "Verify your email address"
                message = f"""
Hello,

Please verify your email address by clicking the link below:

{verify_url}

This link will expire in 24 hours.

If you didn't sign up for an account, please ignore this email.

Best regards,
PriceSynC Team
                """
            
            elif token_type == 'password_reset':
                reset_url = f"{base_url}/reset-password?token={token}"
                subject = "Reset your password"
                message = f"""
Hello,

You requested to reset your password. Click the link below to set a new password:

{reset_url}

This link will expire in 1 hour.

If you didn't request a password reset, please ignore this email.

Best regards,
PriceSynC Team
                """
            
            elif token_type == 'magic_link':
                login_url = f"{base_url}/magic-login?token={token}"
                subject = "Login to your account"
                message = f"""
Hello,

Click the link below to log in to your account:

{login_url}

This link will expire in 15 minutes.

If you didn't request this login link, please ignore this email.

Best regards,
PriceSynC Team
                """
            else:
                raise ValueError(f"Unknown token type: {token_type}")
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        
        await _send()
