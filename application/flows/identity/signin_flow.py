"""
Signin Flow Orchestrator.

Multi-step flow:
1. Authenticate user (core/identity)
2. Create session
"""
import logging
from typing import Optional

from application.dto.identity import (
    SigninCommand,
    SigninContext,
    SigninResult,
)
from core.identity.services.providers import get_identity_service

logger = logging.getLogger(__name__)


class SigninFlow:
    """
    Signin flow orchestrator.
    
    Orchestrates user authentication and session creation.
    """
    
    def __init__(
        self,
        config: dict,
        identity_service=None,
    ):
        """
        Initialize signin flow.
        
        Args:
            config: Identity flow config from identity.yaml
            identity_service: Injected identity service
        """
        self.config = config
        self.identity_service = identity_service or get_identity_service()
    
    async def execute(self, command: SigninCommand) -> SigninResult:
        """
        Execute signin flow.
        
        Args:
            command: SigninCommand with email, password
        
        Returns:
            SigninResult with success/error and session token
        """
        context = SigninContext(email=command.email)
        
        try:
            # Step 1: Authenticate user
            logger.info(f"[Signin Flow] Step 1: Authenticating user {command.email}")
            auth_token, identity = await self._authenticate_step(command, context)
            
            # Step 2: Create session token (use issued token)
            logger.info(f"[Signin Flow] Step 2: Creating session token")
            session_token = await self._create_session_step(auth_token, identity)
            context.mark_authenticated(identity.id, session_token)
            
            return SigninResult(
                success=True,
                identity_id=identity.id,
                session_token=session_token,
                message="Signin successful",
            )
        
        except Exception as e:
            logger.error(f"[Signin Flow] Error: {str(e)}", exc_info=True)
            context.errors["signin_error"] = str(e)
            return SigninResult(
                success=False,
                error=str(e),
                message="Signin failed",
            )
    
    async def _authenticate_step(self, command: SigninCommand, context: SigninContext):
        """
        Step 1: Authenticate user.
        
        Uses core.identity IdentityService.authenticate(email, password) which returns an AuthToken
        (token, user_id). Fetch identity separately to inspect verification state.
        """
        # IdentityService.authenticate signature: (email: str, password: str) -> AuthToken
        auth_token = await self.identity_service.authenticate(command.email, command.password)

        identity = await self.identity_service.get_identity_by_email(command.email)
        if not identity:
            raise ValueError("Identity not found after authentication")

        if self._is_email_verification_required() and not identity.email_verified:
            raise ValueError("Email verification required. Please verify your email first.")

        context.identity_id = identity.id
        return auth_token, identity
    
    async def _create_session_step(self, auth_token, identity) -> str:
        """
        Step 2: Create session token.
        
        Currently IdentityService.authenticate already issues a token via repository.issue_token,
        returning AuthToken. Use that token directly; fallback to string if repository returns plain str.
        """
        token_value = getattr(auth_token, "token", None) or auth_token
        return str(token_value)
    
    def _is_email_verification_required(self) -> bool:
        """Check if email verification is required for signin."""
        return (
            self.config
            .get("flows", {})
            .get("signin", {})
            .get("features", {})
            .get("require_email_verified", True)
        )
