"""
Application layer DTOs for identity flows.

These DTOs coordinate between:
- API layer (HTTP request/response)
- Flow orchestrators (multi-step sequences)
- Module services (core/identity, core/notification, etc.)
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID


# ============================================================
# SIGNUP FLOW DTOs
# ============================================================

@dataclass
class SignupCommand:
    """Input to signup flow."""
    email: str
    password: str
    password_confirm: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@dataclass
class SignupContext:
    """State maintained across signup flow steps."""
    email: str
    identity_id: Optional[UUID] = None
    verification_token: Optional[str] = None
    verification_sent: bool = False
    tenant_id: Optional[UUID] = None
    role_assigned: bool = False
    welcome_email_sent: bool = False
    errors: Dict[str, Any] = field(default_factory=dict)
    
    def mark_user_created(self, identity_id: UUID):
        """Record user creation."""
        self.identity_id = identity_id
    
    def mark_verification_sent(self, token: str):
        """Record verification email sent."""
        self.verification_token = token
        self.verification_sent = True


@dataclass
class SignupResult:
    """Output from signup flow."""
    success: bool
    identity_id: Optional[UUID] = None
    email: Optional[str] = None
    email_verification_required: bool = True
    message: str = ""
    error: Optional[str] = None


# ============================================================
# SIGNIN FLOW DTOs
# ============================================================

@dataclass
class SigninCommand:
    """Input to signin flow."""
    email: str
    password: str


@dataclass
class SigninContext:
    """State maintained across signin flow steps."""
    email: str
    identity_id: Optional[UUID] = None
    authenticated: bool = False
    session_token: Optional[str] = None
    errors: Dict[str, Any] = field(default_factory=dict)
    
    def mark_authenticated(self, identity_id: UUID, session_token: str):
        """Record successful authentication."""
        self.identity_id = identity_id
        self.authenticated = True
        self.session_token = session_token


@dataclass
class SigninResult:
    """Output from signin flow."""
    success: bool
    identity_id: Optional[UUID] = None
    session_token: Optional[str] = None
    message: str = ""
    error: Optional[str] = None


# ============================================================
# PASSWORD RECOVERY FLOW DTOs
# ============================================================

@dataclass
class PasswordRecoveryCommand:
    """Input to password recovery flow."""
    email: str


@dataclass
class PasswordRecoveryContext:
    """State maintained across password recovery flow steps."""
    email: str
    reset_token: Optional[str] = None
    reset_email_sent: bool = False
    reset_confirmed: bool = False
    confirmation_email_sent: bool = False
    errors: Dict[str, Any] = field(default_factory=dict)
    
    def mark_reset_requested(self, token: str):
        """Record reset token generated."""
        self.reset_token = token
        self.reset_email_sent = True
    
    def mark_reset_confirmed(self):
        """Record reset token confirmed."""
        self.reset_confirmed = True


@dataclass
class PasswordRecoveryResult:
    """Output from password recovery flow."""
    success: bool
    email: Optional[str] = None
    reset_email_sent: bool = False
    message: str = ""
    error: Optional[str] = None


# ============================================================
# CONFIRM PASSWORD RESET FLOW DTOs
# ============================================================

@dataclass
class PasswordResetConfirmCommand:
    """Input to password reset confirmation flow."""
    token: str
    new_password: str
    new_password_confirm: str


@dataclass
class PasswordResetConfirmContext:
    """State maintained across password reset confirmation flow steps."""
    token: str
    identity_id: Optional[UUID] = None
    email: Optional[str] = None
    reset_confirmed: bool = False
    confirmation_email_sent: bool = False
    errors: Dict[str, Any] = field(default_factory=dict)
    
    def mark_password_changed(self, identity_id: UUID, email: str):
        """Record successful password change."""
        self.identity_id = identity_id
        self.email = email
        self.reset_confirmed = True


@dataclass
class PasswordResetConfirmResult:
    """Output from password reset confirmation flow."""
    success: bool
    identity_id: Optional[UUID] = None
    email: Optional[str] = None
    confirmation_email_sent: bool = False
    message: str = ""
    error: Optional[str] = None


# ============================================================
# EMAIL VERIFICATION FLOW DTOs
# ============================================================

@dataclass
class VerifyEmailCommand:
    """Input to email verification flow."""
    token: str


@dataclass
class VerifyEmailContext:
    """State maintained across email verification flow steps."""
    token: str
    identity_id: Optional[UUID] = None
    email: Optional[str] = None
    email_verified: bool = False
    welcome_email_sent: bool = False
    errors: Dict[str, Any] = field(default_factory=dict)
    
    def mark_email_verified(self, identity_id: UUID, email: str):
        """Record email verification."""
        self.identity_id = identity_id
        self.email = email
        self.email_verified = True


@dataclass
class VerifyEmailResult:
    """Output from email verification flow."""
    success: bool
    identity_id: Optional[UUID] = None
    email: Optional[str] = None
    email_verified: bool = False
    welcome_email_sent: bool = False
    message: str = ""
    error: Optional[str] = None


# ============================================================
# REQUEST EMAIL VERIFICATION FLOW DTOs
# ============================================================

@dataclass
class RequestVerificationEmailCommand:
    """Input to resend verification email flow."""
    email: str


@dataclass
class RequestVerificationEmailContext:
    """State maintained across resend verification email flow steps."""
    email: str
    verification_token: Optional[str] = None
    verification_email_sent: bool = False
    errors: Dict[str, Any] = field(default_factory=dict)
    
    def mark_verification_sent(self, token: str):
        """Record verification email sent."""
        self.verification_token = token
        self.verification_email_sent = True


@dataclass
class RequestVerificationEmailResult:
    """Output from resend verification email flow."""
    success: bool
    email: Optional[str] = None
    verification_email_sent: bool = False
    message: str = ""
    error: Optional[str] = None


__all__ = [
    "SignupCommand",
    "SignupContext",
    "SignupResult",
    "SigninCommand",
    "SigninContext",
    "SigninResult",
    "PasswordRecoveryCommand",
    "PasswordRecoveryContext",
    "PasswordRecoveryResult",
    "PasswordResetConfirmCommand",
    "PasswordResetConfirmContext",
    "PasswordResetConfirmResult",
    "VerifyEmailCommand",
    "VerifyEmailContext",
    "VerifyEmailResult",
    "RequestVerificationEmailCommand",
    "RequestVerificationEmailContext",
    "RequestVerificationEmailResult",
]


@dataclass(frozen=True)
class RecoverPasswordCommand:
    """Command to initiate password recovery."""
    email: str


@dataclass(frozen=True)
class RecoverPasswordResult:
    """Result of password recovery initiation."""
    recovery_token: Optional[str]
    sent: bool
