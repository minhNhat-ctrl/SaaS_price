"""
Signup Flow Orchestrator.

Multi-step flow:
1. Register user (core/identity)
2. Send verification email (core/notification)
3. Auto-create tenant (optional, core/provisioning)
4. Assign default role (optional, core/access)
"""
import logging
from typing import Optional
from uuid import uuid4
from asgiref.sync import sync_to_async

from application.dto.identity import (
    SignupCommand,
    SignupContext,
    SignupResult,
)
from core.identity.services.providers import get_identity_service
from core.notification.services.providers import get_notification_service

logger = logging.getLogger(__name__)


class SignupFlow:
    """
    Signup flow orchestrator.
    
    Orchestrates multi-step user signup process:
    - Register user with identity service
    - Send verification email via notification service
    - Auto-create tenant (if enabled)
    - Assign default role (if enabled)
    """
    
    def __init__(
        self,
        config: dict,
        identity_service=None,
        notification_service=None,
    ):
        """
        Initialize signup flow.
        
        Args:
            config: Identity flow config from identity.yaml
            identity_service: Injected identity service (or will fetch from provider)
            notification_service: Injected notification service (or will fetch from provider)
        """
        self.config = config
        self.identity_service = identity_service or get_identity_service()
        self.notification_service = notification_service or get_notification_service()
        logger.info(f"[Signup Flow] Initialized with config keys: {list(config.keys())}")
        logger.info(f"[Signup Flow] Flows config: {config.get('flows', {})}")
        logger.info(f"[Signup Flow] Templates config: {config.get('templates', {})}")
    
    async def execute(self, command: SignupCommand) -> SignupResult:
        """
        Execute signup flow.
        
        Args:
            command: SignupCommand with email, password, password_confirm
        
        Returns:
            SignupResult with success/error details
        """
        context = SignupContext(email=command.email)
        
        try:
            # Step 1: Register user
            logger.info(f"[Signup Flow] Step 1: Registering user {command.email}")
            user = await self._register_user_step(command, context)
            context.mark_user_created(user.id)
            
            # Step 2: Send verification email
            if self._is_email_verification_enabled():
                logger.info(f"[Signup Flow] Step 2: Sending verification email")
                await self._send_verification_email_step(user, context)
            
            # Step 3: Auto-create tenant (optional)
            if self._is_auto_create_tenant_enabled():
                logger.info(f"[Signup Flow] Step 3: Auto-creating tenant")
                await self._auto_create_tenant_step(user, context)
            
            # Step 4: Assign default role (optional)
            if self._is_assign_default_role_enabled():
                logger.info(f"[Signup Flow] Step 4: Assigning default role")
                await self._assign_default_role_step(user, context)
            
            return SignupResult(
                success=True,
                identity_id=user.id,
                email=user.email,
                email_verification_required=self._is_email_verification_enabled(),
                message="User registered successfully",
            )
        
        except Exception as e:
            logger.error(f"[Signup Flow] Error: {str(e)}", exc_info=True)
            context.errors["signup_error"] = str(e)
            return SignupResult(
                success=False,
                email=command.email,
                error=str(e),
                message="Signup failed",
            )
    
    async def _register_user_step(self, command: SignupCommand, context: SignupContext):
        """
        Step 1: Register user with core/identity.
        
        Args:
            command: SignupCommand
            context: SignupContext to update
        
        Returns:
            User entity from identity service
        
        Raises:
            Exception from identity service (validation, duplicate email, etc.)
        """
        from core.identity.dto.contracts import RegisterIdentityCommand
        
        # Identity service register_user() signature: (email, password, email_verified)
        # No need for password_confirm (already validated at API layer)
        user = await self.identity_service.register_user(
            email=command.email,
            password=command.password,
            email_verified=False,
        )
        return user
    
    async def _send_verification_email_step(self, user, context: SignupContext):
        """
        Step 2: Send verification email via core/notification.
        
        Args:
            user: User entity from identity service
            context: SignupContext to update
        """
        from core.notification.dto.contracts import VerificationEmailCommand
        
        logger.info(f"[Signup Flow] Starting verification email step for {user.email}")
        
        # Request verification token from identity service (signature: email only)
        token = await self.identity_service.request_email_verification(user.email)
        logger.info(f"[Signup Flow] Got verification token: {token[:20]}...")
        context.mark_verification_sent(token)
        
        # Send verification email
        frontend_url = self.config["flows"]["signup"]["features"]["email_verification"].get(
            "frontend_url",
            self.config.get("frontend", {}).get("verify_email_url", ""),
        )
        logger.info(f"[Signup Flow] Frontend URL: {frontend_url}")
        
        verify_cmd = VerificationEmailCommand(
            recipient_email=user.email,
            verification_token=token,
            verification_url=f"{frontend_url}?token={token}",
            language="en",
            sender_key=self.config["templates"]["email_verification"].get("sender_key"),
            template_key=self.config["templates"]["email_verification"].get("template_key", "email_verification"),
        )
        logger.info(f"[Signup Flow] Verification command: sender_key={verify_cmd.sender_key}, template_key={verify_cmd.template_key}")
        
        try:
            logger.info(f"[Signup Flow] Calling notification service to send verification email...")
            log = await sync_to_async(self.notification_service.send_from_dto)(
                verify_cmd.to_send_notification_command()
            )
            logger.info(f"[Signup Flow] Notification log: {log}, status={log.status if hasattr(log, 'status') else 'N/A'}")
            
            if log.status.value != "SENT":
                logger.warning(f"[Signup Flow] Verification email send failed: {log.error_message}")
                context.errors["verification_email_failed"] = log.error_message
            else:
                logger.info(f"[Signup Flow] Verification email sent to {user.email}")
        except Exception as exc:
            # Do not fail signup if email cannot be sent; record error and continue
            logger.error(f"[Signup Flow] Verification email send exception: {exc}", exc_info=True)
            context.errors["verification_email_failed"] = str(exc)
    
    async def _auto_create_tenant_step(self, user, context: SignupContext):
        """
        Step 3: Auto-create tenant (optional).
        
        Placeholder for future tenant provisioning.
        """
        logger.debug(f"[Signup Flow] Auto-create tenant: TODO - wire core/provisioning service")
        # TODO: Implement tenant provisioning
        # tenant = await self.provisioning_service.create_tenant(...)
        # context.tenant_id = tenant.id
    
    async def _assign_default_role_step(self, user, context: SignupContext):
        """
        Step 4: Assign default role (optional).
        
        Placeholder for future role assignment.
        """
        logger.debug(f"[Signup Flow] Assign default role: TODO - wire core/access service")
        # TODO: Implement role assignment
        # role = await self.access_service.assign_role(...)
        # context.role_assigned = True
    
    # ========== Helper Methods ==========
    
    def _is_email_verification_enabled(self) -> bool:
        """Check if email verification is enabled in signup flow."""
        enabled = (
            self.config
            .get("flows", {})
            .get("signup", {})
            .get("features", {})
            .get("email_verification", {})
            .get("enabled", True)
        )
        logger.debug(f"[Signup Flow] Email verification enabled: {enabled}")
        logger.debug(f"[Signup Flow] Config path: flows.signup.features.email_verification.enabled")
        logger.debug(f"[Signup Flow] Full config: {self.config}")
        return enabled
    
    def _is_auto_create_tenant_enabled(self) -> bool:
        """Check if auto-create tenant is enabled."""
        return (
            self.config
            .get("flows", {})
            .get("signup", {})
            .get("features", {})
            .get("auto_create_tenant", {})
            .get("enabled", False)
        )
    
    def _is_assign_default_role_enabled(self) -> bool:
        """Check if assign default role is enabled."""
        return (
            self.config
            .get("flows", {})
            .get("signup", {})
            .get("features", {})
            .get("assign_default_role", {})
            .get("enabled", False)
        )
