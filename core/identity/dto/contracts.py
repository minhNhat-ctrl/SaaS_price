"""Identity module DTO contracts shared with application layer."""
from dataclasses import dataclass
from uuid import UUID
from typing import Optional


@dataclass
class RegisterIdentityCommand:
    email: str
    password: str
    email_verified: bool = False


@dataclass
class RegisterIdentityResult:
    identity_id: UUID
    email: str
    email_verified: bool


@dataclass
class AuthenticationCommand:
    email: str
    password: str


@dataclass
class AuthenticationResult:
    user_id: UUID
    token: str
    expires_in: Optional[int] = None


@dataclass
class PasswordResetRequestCommand:
    """Command to request password reset (initiate recovery flow)."""
    email: str


@dataclass
class PasswordResetRequestResult:
    """Result of password reset request."""
    email: str
    reset_token: str


@dataclass
class PasswordResetConfirmCommand:
    """Command to confirm password reset with token and new password."""
    token: str
    new_password: str


@dataclass
class PasswordResetConfirmResult:
    """Result of password reset confirmation."""
    identity_id: UUID
    email: str
    password_reset: bool


@dataclass
class VerifyEmailCommand:
    """Command to verify email using verification token."""
    token: str


@dataclass
class VerifyEmailResult:
    """Result of email verification."""
    identity_id: UUID
    email: str
    email_verified: bool
