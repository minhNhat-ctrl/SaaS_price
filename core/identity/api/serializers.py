"""Serializers for Identity API adapters.

Currently validation is handled inline in views; migrate logic here when adopting DRF.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class SignupRequestDTO:
    email: str
    password: str
    email_verified: bool = False


@dataclass(slots=True)
class LoginRequestDTO:
    email: str
    password: str
    remember_me: bool = False


@dataclass(slots=True)
class PasswordResetRequestDTO:
    email: str
    redirect_url: Optional[str] = None
