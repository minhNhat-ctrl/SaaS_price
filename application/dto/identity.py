"""Identity domain DTOs (signup, signin, recovery)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SignupCommand:
    """Command to register a new user."""
    email: str
    password: str
    source: str = "web"


@dataclass(frozen=True)
class SignupResult:
    """Result of user signup operation."""
    user_id: str
    verify_required: bool


@dataclass(frozen=True)
class VerifyEmailResult:
    """Result of email verification."""
    verified: bool


@dataclass(frozen=True)
class SigninResult:
    """Result of user sign-in."""
    user_id: str
    session_id: str


@dataclass(frozen=True)
class RecoverPasswordCommand:
    """Command to initiate password recovery."""
    email: str


@dataclass(frozen=True)
class RecoverPasswordResult:
    """Result of password recovery initiation."""
    recovery_token: Optional[str]
    sent: bool
