"""Tenant onboarding flow - orchestrates full provisioning from signup to activation."""
from __future__ import annotations

from dataclasses import replace
from enum import Enum
from typing import Optional

from ...contracts.identity import SignupHandler, VerifyEmailHandler, SigninHandler
from ...contracts.provisioning import (
    CreateTenantHandler,
    ResolveSubscriptionHandler,
    AssignPlanHandler,
    QuoteHandler,
    ChargeHandler,
    ActivateTenantHandler,
)
from ...dto.identity import SignupCommand
from ...services.flow_context import FlowContext


class ProvisioningStep(str, Enum):
    """Steps in the tenant onboarding flow."""
    SIGNUP = "signup"
    VERIFY_EMAIL = "verify_email"
    SIGNIN = "signin"
    CREATE_TENANT = "create_tenant"
    RESOLVE_SUBSCRIPTION = "resolve_subscription"
    ASSIGN_PLAN = "assign_plan"
    QUOTE_PAYMENT = "quote_payment"
    ACTIVATE_TENANT = "activate_tenant"


class TenantOnboardingFlow:
    """
    Orchestrates the complete tenant provisioning flow.
    
    This flow coordinates multiple domains (identity, subscription, billing)
    to onboard a new customer from signup through tenant activation.
    
    Each step is toggle-controlled and can be skipped if disabled.
    """
    
    FLOW_CODE = "provisioning"
    
    def __init__(
        self,
        signup_handler: SignupHandler,
        verify_handler: Optional[VerifyEmailHandler] = None,
        signin_handler: Optional[SigninHandler] = None,
        create_tenant_handler: Optional[CreateTenantHandler] = None,
        resolve_subscription_handler: Optional[ResolveSubscriptionHandler] = None,
        assign_plan_handler: Optional[AssignPlanHandler] = None,
        quote_handler: Optional[QuoteHandler] = None,
        charge_handler: Optional[ChargeHandler] = None,
        activate_handler: Optional[ActivateTenantHandler] = None,
    ) -> None:
        self.signup_handler = signup_handler
        self.verify_handler = verify_handler
        self.signin_handler = signin_handler
        self.create_tenant_handler = create_tenant_handler
        self.resolve_subscription_handler = resolve_subscription_handler
        self.assign_plan_handler = assign_plan_handler
        self.quote_handler = quote_handler
        self.charge_handler = charge_handler
        self.activate_handler = activate_handler
    
    def run(self, command: SignupCommand) -> FlowContext:
        """Execute the full onboarding flow starting from signup command."""
        context = FlowContext()
        
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
    
    def _execute_signup_step(self, context: FlowContext, command: SignupCommand) -> FlowContext:
        """Step 1: Register new user."""
        result = self.signup_handler(command)
        context.user_id = result.user_id
        context.set_meta("verify_required", str(result.verify_required))
        return context
    
    def _execute_verify_email_step(self, context: FlowContext) -> FlowContext:
        """Step 2: Verify user email."""
        if not self.verify_handler:
            return context
        
        result = self.verify_handler(context)
        context.set_meta("email_verified", str(result.verified))
        return context
    
    def _execute_signin_step(self, context: FlowContext) -> FlowContext:
        """Step 3: Sign in user to establish session."""
        if not self.signin_handler:
            return context
        
        result = self.signin_handler(context)
        context.user_id = result.user_id
        context.session_id = result.session_id
        return context
    
    def _execute_create_tenant_step(self, context: FlowContext) -> FlowContext:
        """Step 4: Create tenant for user."""
        if not self.create_tenant_handler:
            return context
        
        result = self.create_tenant_handler(context)
        context.tenant_id = result.tenant_id
        context.set_meta("tenant_status", result.status)
        return context
    
    def _execute_resolve_subscription_step(self, context: FlowContext) -> FlowContext:
        """Step 5: Resolve subscription terms (trial, plan selection)."""
        if not self.resolve_subscription_handler:
            return context
        
        result = self.resolve_subscription_handler(context)
        context.subscription_status = result.status
        context.set_meta("trial_days", str(result.trial_days or ""))
        return context
    
    def _execute_assign_plan_step(self, context: FlowContext) -> FlowContext:
        """Step 6: Assign pricing plan to tenant."""
        if not self.assign_plan_handler:
            return context
        
        result = self.assign_plan_handler(context)
        context.plan_code = result.plan_code
        context.requires_payment = result.requires_payment
        context.set_meta("requires_payment", str(result.requires_payment))
        return context
    
    def _execute_quote_payment_step(self, context: FlowContext) -> FlowContext:
        """Step 7: Quote and charge payment if required."""
        if context.requires_payment:
            if self.quote_handler:
                quote_result = self.quote_handler(context)
                context.quote_id = quote_result.quote_id
                context.set_meta("quote_amount", str(quote_result.amount))
                context.set_meta("quote_currency", quote_result.currency)
            
            if self.charge_handler:
                charge_result = self.charge_handler(context)
                context.set_meta("payment_success", str(charge_result.success))
                context.set_meta("transaction_id", charge_result.transaction_id or "")
        
        return context
    
    def _execute_activate_tenant_step(self, context: FlowContext) -> FlowContext:
        """Step 8: Activate tenant (final step)."""
        if not self.activate_handler:
            return context
        
        result = self.activate_handler(context)
        context.set_meta("activation_status", result.status)
        return context
