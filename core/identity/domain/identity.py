"""
Domain entities for Identity module.

Rules:
- No Django imports
- No persistence concerns
- No HTTP/session concerns

Entities:
- UserIdentity: canonical identity record
- Credential: password representation (plaintext only at service layer, never stored here)
- AuthToken: logical token representation (metadata only)
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from .exceptions import InvalidEmailError, InvalidCredentialError


def _validate_email(email: str) -> bool:
    return bool(email and "@" in email and "." in email)


@dataclass
class UserIdentity:
    id: UUID
    email: str
    is_active: bool = True
    email_verified: bool = False
    mfa_enabled: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if not _validate_email(self.email):
            raise InvalidEmailError(self.email)

    @classmethod
    def create(cls, email: str, is_active: bool = True, email_verified: bool = False) -> "UserIdentity":
        return cls(
            id=uuid4(),
            email=email.strip().lower(),
            is_active=is_active,
            email_verified=email_verified,
        )

    def activate(self):
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def deactivate(self):
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def mark_email_verified(self):
        self.email_verified = True
        self.updated_at = datetime.utcnow()

    def enable_mfa(self):
        self.mfa_enabled = True
        self.updated_at = datetime.utcnow()

    def disable_mfa(self):
        self.mfa_enabled = False
        self.updated_at = datetime.utcnow()


@dataclass
class Credential:
    email: str
    password: str

    def __post_init__(self):
        if not _validate_email(self.email):
            raise InvalidEmailError(self.email)
        if not self.password:
            raise InvalidCredentialError("Password cannot be empty")


@dataclass
class AuthToken:
    """Logical token representation (metadata only)."""
    token: str
    user_id: UUID  # User ID associated with this token
    issued_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
