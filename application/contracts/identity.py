"""Identity flow contracts - Protocol definitions for identity flows."""
from __future__ import annotations

from typing import Protocol

from ..dto.identity import (
    SignupCommand,
    SignupResult,
    VerifyEmailResult,
    SigninResult,
    RecoverPasswordCommand,
    RecoverPasswordResult,
)
from ..services.flow_context import FlowContext


class SignupHandler(Protocol):
    """Handler for user signup."""
    
    def __call__(self, command: SignupCommand) -> SignupResult:
        """Execute signup and return result."""
        ...


class VerifyEmailHandler(Protocol):
    """Handler for email verification."""
    
    def __call__(self, context: FlowContext) -> VerifyEmailResult:
        """Verify user email based on context."""
        ...


class SigninHandler(Protocol):
    """Handler for user sign-in."""
    
    def __call__(self, context: FlowContext) -> SigninResult:
        """Sign in user and return session."""
        ...


class RecoverPasswordHandler(Protocol):
    """Handler for password recovery."""
    
    def __call__(self, command: RecoverPasswordCommand) -> RecoverPasswordResult:
        """Initiate password recovery."""
        ...
