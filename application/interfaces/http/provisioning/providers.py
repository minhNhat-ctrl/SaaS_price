"""Provisioning orchestrator provider (dependency injection factory)."""
from typing import Optional

from application.flow_rules.services.toggles import FlowToggleService
from application.orchestrators.provisioning import ProvisioningFlowOrchestrator
from application.orchestrators.provisioning import (
    SignupHandler,
    VerifyHandler,
    SigninHandler,
    CreateTenantHandler,
    ResolveSubscriptionHandler,
    AssignPlanHandler,
    QuoteHandler,
    ChargeHandler,
    ActivateHandler,
)


class ProvisioningOrchestratorProvider:
    """Factory for creating configured ProvisioningFlowOrchestrator instances."""

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
        """
        Initialize provider with handlers.
        
        Args:
            toggle_service: Flow toggle service for reading step toggles
            signup_handler: Required handler for signup step
            verify_handler: Optional handler for email verification step
            signin_handler: Optional handler for signin step
            create_tenant_handler: Optional handler for tenant creation step
            resolve_subscription_handler: Optional handler for subscription resolution
            assign_plan_handler: Optional handler for plan assignment
            quote_handler: Optional handler for payment quoting
            charge_handler: Optional handler for payment charging
            activate_handler: Optional handler for tenant activation
        """
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

    def create(self) -> ProvisioningFlowOrchestrator:
        """Create configured orchestrator instance."""
        return ProvisioningFlowOrchestrator(
            toggle_service=self.toggle_service,
            signup_handler=self.signup_handler,
            verify_handler=self.verify_handler,
            signin_handler=self.signin_handler,
            create_tenant_handler=self.create_tenant_handler,
            resolve_subscription_handler=self.resolve_subscription_handler,
            assign_plan_handler=self.assign_plan_handler,
            quote_handler=self.quote_handler,
            charge_handler=self.charge_handler,
            activate_handler=self.activate_handler,
        )


# Global provider instance (to be initialized in apps.py)
_provider: Optional[ProvisioningOrchestratorProvider] = None


def get_provisioning_orchestrator_provider() -> Optional[ProvisioningOrchestratorProvider]:
    """Get the configured provisioning orchestrator provider."""
    return _provider


def set_provisioning_orchestrator_provider(provider: ProvisioningOrchestratorProvider) -> None:
    """Set the global provisioning orchestrator provider."""
    global _provider
    _provider = provider


def get_provisioning_orchestrator() -> Optional[ProvisioningFlowOrchestrator]:
    """Get a provisioning orchestrator instance."""
    provider = get_provisioning_orchestrator_provider()
    if not provider:
        return None
    return provider.create()
