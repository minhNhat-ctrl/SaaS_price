"""Provisioning flow orchestrator coordinating core modules."""
from __future__ import annotations

from dataclasses import replace
from enum import Enum
from typing import Callable, Optional

from .base import Orchestrator
from ..dto.provisioning import (
    ActivateTenantResult,
    AssignPlanResult,
    ChargePaymentResult,
    CreateQuoteResult,
    CreateTenantResult,
    ProvisioningContext,
    ResolveSubscriptionResult,
    SigninResult,
    SignupCommand,
    SignupResult,
    VerifyEmailResult,
)
from ..flow_rules.services.toggles import FlowToggleService


class ProvisioningStep(str, Enum):
    SIGNUP = "signup"
    VERIFY_EMAIL = "verify_email"
    SIGNIN = "signin"
    CREATE_TENANT = "create_tenant"
    RESOLVE_SUBSCRIPTION = "resolve_subscription"
    ASSIGN_PLAN = "assign_plan"
    QUOTE_PAYMENT = "quote_payment"
    ACTIVATE_TENANT = "activate_tenant"


SignupHandler = Callable[[SignupCommand], SignupResult]
ContextHandler = Callable[[ProvisioningContext], ProvisioningContext]
VerifyHandler = Callable[[ProvisioningContext], VerifyEmailResult]
SigninHandler = Callable[[ProvisioningContext], SigninResult]
CreateTenantHandler = Callable[[ProvisioningContext], CreateTenantResult]
ResolveSubscriptionHandler = Callable[[ProvisioningContext], ResolveSubscriptionResult]
AssignPlanHandler = Callable[[ProvisioningContext], AssignPlanResult]
QuoteHandler = Callable[[ProvisioningContext], CreateQuoteResult]
ChargeHandler = Callable[[ProvisioningContext], ChargePaymentResult]
ActivateHandler = Callable[[ProvisioningContext], ActivateTenantResult]


class ProvisioningFlowOrchestrator(Orchestrator):
    """Runs the fixed provisioning flow while respecting admin toggles."""

    FLOW_CODE = "provisioning"

    def __init__(
        self,
        toggle_service: FlowToggleService,
        signup_handler: SignupHandler,
        verify_handler: Optional[VerifyHandler] = None,
        signin_handler: Optional[SigninHandler] = None,
        create_tenant_handler: Optional[CreateTenantHandler] = None,
        resolve_subscription_handler: Optional[ResolveSubscriptionHandler] = None,
        assign_plan_handler: Optional[AssignPlanHandler] = None,
        quote_handler: Optional[QuoteHandler] = None,
        charge_handler: Optional[ChargeHandler] = None,
        activate_handler: Optional[ActivateHandler] = None,
    ) -> None:
        self.toggle_service = toggle_service
        self.signup_handler = signup_handler
        self.verify_handler = verify_handler
        self.signin_handler = signin_handler
        self.create_tenant_handler = create_tenant_handler
        self.resolve_subscription_handler = resolve_subscription_handler
        self.assign_plan_handler = assign_plan_handler
        self.quote_handler = quote_handler
        self.charge_handler = charge_handler
        self.activate_handler = activate_handler

    def run(self, command: SignupCommand) -> ProvisioningContext:
        """Execute the provisioning sequence starting from signup."""
        context = ProvisioningContext()
        context = self._execute_signup_step(context, command)
        context = self._execute_verify_email_step(context)
        context = self._execute_signin_step(context)
        context = self._execute_create_tenant_step(context)
        context = self._execute_resolve_subscription_step(context)
        context = self._execute_assign_plan_step(context)
        context = self._execute_quote_payment_step(context)
        context = self._execute_activate_tenant_step(context)
        return context

    # Step executors -----------------------------------------------------

    def _execute_signup_step(self, context: ProvisioningContext, command: SignupCommand) -> ProvisioningContext:
        if not self._is_enabled(ProvisioningStep.SIGNUP):
            return context
        result = self.signup_handler(command)
        updated = replace(
            context,
            user_id=result.user_id,
        )
        metadata = (updated.metadata or {}).copy()
        metadata["verify_required"] = str(result.verify_required)
        updated.metadata = metadata
        return updated

    def _execute_verify_email_step(self, context: ProvisioningContext) -> ProvisioningContext:
        if not self._is_enabled(ProvisioningStep.VERIFY_EMAIL):
            return context
        if not self.verify_handler:
            return context
        result = self.verify_handler(context)
        metadata = (context.metadata or {}).copy()
        metadata["email_verified"] = str(result.verified)
        context.metadata = metadata
        return context

    def _execute_signin_step(self, context: ProvisioningContext) -> ProvisioningContext:
        if not self._is_enabled(ProvisioningStep.SIGNIN):
            return context
        if not self.signin_handler:
            return context
        result = self.signin_handler(context)
        metadata = (context.metadata or {}).copy()
        metadata["session_id"] = result.session_id
        context.metadata = metadata
        return replace(context, user_id=result.user_id)

    def _execute_create_tenant_step(self, context: ProvisioningContext) -> ProvisioningContext:
        if not self._is_enabled(ProvisioningStep.CREATE_TENANT):
            return context
        if not self.create_tenant_handler:
            return context
        result = self.create_tenant_handler(context)
        metadata = (context.metadata or {}).copy()
        metadata["tenant_status"] = result.status
        context.metadata = metadata
        return replace(context, tenant_id=result.tenant_id)

    def _execute_resolve_subscription_step(self, context: ProvisioningContext) -> ProvisioningContext:
        if not self._is_enabled(ProvisioningStep.RESOLVE_SUBSCRIPTION):
            return context
        if not self.resolve_subscription_handler:
            return context
        result = self.resolve_subscription_handler(context)
        metadata = (context.metadata or {}).copy()
        metadata["trial_days"] = str(result.trial_days or "")
        context.metadata = metadata
        return replace(context, subscription_status=result.status)

    def _execute_assign_plan_step(self, context: ProvisioningContext) -> ProvisioningContext:
        if not self._is_enabled(ProvisioningStep.ASSIGN_PLAN):
            return context
        if not self.assign_plan_handler:
            return context
        result = self.assign_plan_handler(context)
        metadata = (context.metadata or {}).copy()
        metadata["requires_payment"] = str(result.requires_payment)
        context.metadata = metadata
        return replace(context, plan_code=result.plan_code, requires_payment=result.requires_payment)

    def _execute_quote_payment_step(self, context: ProvisioningContext) -> ProvisioningContext:
        if not self._is_enabled(ProvisioningStep.QUOTE_PAYMENT):
            return context
        if context.requires_payment:
            if self.quote_handler:
                quote_result = self.quote_handler(context)
                context = replace(context, quote_id=quote_result.quote_id)
                metadata = (context.metadata or {}).copy()
                metadata["quote_amount"] = str(quote_result.amount)
                metadata["quote_currency"] = quote_result.currency
                context.metadata = metadata
            if self.charge_handler:
                charge_result = self.charge_handler(context)
                metadata = (context.metadata or {}).copy()
                metadata["payment_success"] = str(charge_result.success)
                metadata["transaction_id"] = charge_result.transaction_id or ""
                context.metadata = metadata
        return context

    def _execute_activate_tenant_step(self, context: ProvisioningContext) -> ProvisioningContext:
        if not self._is_enabled(ProvisioningStep.ACTIVATE_TENANT):
            return context
        if not self.activate_handler:
            return context
        result = self.activate_handler(context)
        metadata = (context.metadata or {}).copy()
        metadata["activation_status"] = result.status
        context.metadata = metadata
        return context

    # Helpers ------------------------------------------------------------

    def _is_enabled(self, step: ProvisioningStep) -> bool:
        return self.toggle_service.is_step_enabled(self.FLOW_CODE, step.value)
