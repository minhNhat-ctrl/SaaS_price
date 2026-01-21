"""Providers for identity flows.

This keeps config loading and flow wiring out of the API layer.
"""
from application.flows.identity import (
    SignupFlow,
    SigninFlow,
    PasswordRecoveryFlow,
)
from application.services.config_loader import load_identity_config


def get_signup_flow() -> SignupFlow:
    """Create SignupFlow with identity.yaml config."""
    config = load_identity_config()
    return SignupFlow(config=config)


def get_signin_flow() -> SigninFlow:
    """Create SigninFlow with identity.yaml config."""
    config = load_identity_config()
    return SigninFlow(config=config)


def get_password_recovery_flow() -> PasswordRecoveryFlow:
    """Create PasswordRecoveryFlow with identity.yaml config."""
    config = load_identity_config()
    return PasswordRecoveryFlow(config=config)
