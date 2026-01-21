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
            user = await self._authenticate_step(command, context)
            context.identity_id = user.id
            
            # Step 2: Create session token
            logger.info(f"[Signin Flow] Step 2: Creating session token")
            session_token = await self._create_session_step(user, context)
            context.mark_authenticated(user.id, session_token)
            
            return SigninResult(
                success=True,
                identity_id=user.id,
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
        
        Args:
            command: SigninCommand
            context: SigninContext to update
        
        Returns:
            User entity from identity service
        
        Raises:
            Exception from identity service (invalid credentials, etc.)
        """
        from core.identity.dto.contracts import AuthenticationCommand
        
        auth_cmd = AuthenticationCommand(
            email=command.email,
            password=command.password,
        )
        
        user = await self.identity_service.authenticate(auth_cmd)
        
        # Check if email verification is required
        if self._is_email_verification_required() and not user.email_verified:
            raise ValueError("Email verification required. Please verify your email first.")
        
        return user
    
    async def _create_session_step(self, user, context: SigninContext) -> str:
        """
        Step 2: Create session token.
        
        Args:
            user: User entity
            context: SigninContext to update
        
        Returns:
            Session token (JWT or opaque token)
        """
        # TODO: Implement session token creation
        # For now, return a placeholder
        import uuid
        return str(uuid.uuid4())
    
    def _is_email_verification_required(self) -> bool:
        """Check if email verification is required for signin."""
        return (
            self.config
            .get("flows", {})
            .get("signin", {})
            .get("features", {})
            .get("require_email_verified", True)
        )
