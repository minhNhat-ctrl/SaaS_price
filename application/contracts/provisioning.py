"""Provisioning flow contracts - Protocol definitions for tenant provisioning."""
from __future__ import annotations

from typing import Protocol

from ..dto.tenant import (
    CreateTenantResult,
    ResolveSubscriptionResult,
    AssignPlanResult,
    ActivateTenantResult,
)
from ..dto.billing import CreateQuoteResult, ChargePaymentResult
from ..services.flow_context import FlowContext


class CreateTenantHandler(Protocol):
    """Handler for tenant creation."""
    
    def __call__(self, context: FlowContext) -> CreateTenantResult:
        """Create tenant from context."""
        ...


class ResolveSubscriptionHandler(Protocol):
    """Handler for subscription resolution."""
    
    def __call__(self, context: FlowContext) -> ResolveSubscriptionResult:
        """Resolve subscription terms."""
        ...


class AssignPlanHandler(Protocol):
    """Handler for plan assignment."""
    
    def __call__(self, context: FlowContext) -> AssignPlanResult:
        """Assign plan to tenant."""
        ...


class QuoteHandler(Protocol):
    """Handler for payment quote creation."""
    
    def __call__(self, context: FlowContext) -> CreateQuoteResult:
        """Create payment quote."""
        ...


class ChargeHandler(Protocol):
    """Handler for payment charge."""
    
    def __call__(self, context: FlowContext) -> ChargePaymentResult:
        """Charge payment."""
        ...


class ActivateTenantHandler(Protocol):
    """Handler for tenant activation."""
    
    def __call__(self, context: FlowContext) -> ActivateTenantResult:
        """Activate tenant."""
        ...
