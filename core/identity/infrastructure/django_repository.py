"""
Django-allauth based repository implementation for Identity module.

Responsibilities:
- Map Django/allauth models to domain entities
- Handle password hashing & verification
- Issue logical tokens (stateless token generator)

Constraints:
- No tenant, no role logic
- Acts as adapter; services stay framework-agnostic
"""
import secrets
from typing import Optional
from uuid import UUID

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.tokens import default_token_generator
from allauth.account.models import EmailAddress

from core.identity.domain.identity import UserIdentity, Credential, AuthToken
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
