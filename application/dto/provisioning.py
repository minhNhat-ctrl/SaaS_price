"""Data transfer objects for provisioning flow."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SignupCommand:
    email: str
    password: str
    source: str = "web"


@dataclass(frozen=True)
class SignupResult:
    user_id: str
    verify_required: bool


@dataclass(frozen=True)
class VerifyEmailResult:
    verified: bool


@dataclass(frozen=True)
class SigninResult:
    user_id: str
    session_id: str


@dataclass(frozen=True)
class CreateTenantResult:
    tenant_id: str
    status: str


@dataclass(frozen=True)
class ResolveSubscriptionResult:
    status: str
    trial_days: Optional[int] = None


@dataclass(frozen=True)
class AssignPlanResult:
    plan_code: str
    requires_payment: bool


@dataclass(frozen=True)
class CreateQuoteResult:
    quote_id: str
    amount: float
    currency: str


@dataclass(frozen=True)
class ChargePaymentResult:
    success: bool
    transaction_id: Optional[str]


@dataclass(frozen=True)
class ActivateTenantResult:
    status: str


@dataclass
class ProvisioningContext:
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    plan_code: Optional[str] = None
    subscription_status: Optional[str] = None
    quote_id: Optional[str] = None
    requires_payment: bool = False
    metadata: dict[str, str] | None = None
