"""Provider for onboarding flow - wires dependencies."""
from typing import Optional

from application.flows.provisioning.tenant_onboarding_flow import TenantOnboardingFlow
from application.flow_rules.services.toggles import get_flow_toggle_service


# Global instance
_onboarding_flow: Optional[TenantOnboardingFlow] = None


def _default_signup_handler(command):
    """Placeholder signup handler."""
    from application.dto.identity import SignupResult
    return SignupResult(user_id=str(__import__('uuid').uuid4()), verify_required=True)


def get_onboarding_flow() -> Optional[TenantOnboardingFlow]:
    """Get the global onboarding flow instance."""
    return _onboarding_flow


def set_onboarding_flow(flow: TenantOnboardingFlow) -> None:
    """Set the global onboarding flow instance."""
    global _onboarding_flow
    _onboarding_flow = flow


def create_onboarding_flow(
    signup_handler=None,
    verify_handler=None,
    signin_handler=None,
    create_tenant_handler=None,
    resolve_subscription_handler=None,
    assign_plan_handler=None,
    quote_handler=None,
    charge_handler=None,
    activate_handler=None,
) -> TenantOnboardingFlow:
    """
    Factory to create onboarding flow with dependency injection.
    
    If handlers are not provided, uses defaults/placeholders.
    """
    toggle_service = get_flow_toggle_service()
    
    return TenantOnboardingFlow(
        toggle_service=toggle_service,
        signup_handler=signup_handler or _default_signup_handler,
        verify_handler=verify_handler,
        signin_handler=signin_handler,
        create_tenant_handler=create_tenant_handler,
        resolve_subscription_handler=resolve_subscription_handler,
        assign_plan_handler=assign_plan_handler,
        quote_handler=quote_handler,
        charge_handler=charge_handler,
        activate_handler=activate_handler,
    )
