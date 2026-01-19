"""Identity module DTO contracts shared with application layer."""
from dataclasses import dataclass
from uuid import UUID
from typing import Optional


@dataclass(slots=True)
class RegisterIdentityCommand:
    email: str
    password: str
    email_verified: bool = False


@dataclass(slots=True)
class RegisterIdentityResult:
    identity_id: UUID
    email: str
    email_verified: bool


@dataclass(slots=True)
class AuthenticationCommand:
    email: str
    password: str


@dataclass(slots=True)
class AuthenticationResult:
    user_id: UUID
    token: str
    expires_in: Optional[int] = None
