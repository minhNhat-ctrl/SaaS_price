"""
Email Verification Flow Orchestrator.

Multi-step flow:
1. Verify email token (core/identity)
2. Send welcome email (core/notification, optional)
"""
import logging

from application.dto.identity import (
    VerifyEmailCommand,
    VerifyEmailContext,
    VerifyEmailResult,
)
from core.identity.services.providers import get_identity_service
from core.notification.services.providers import get_notification_service

logger = logging.getLogger(__name__)


class VerifyEmailFlow:
    """
    Email verification flow orchestrator.
    
    Orchestrates email token verification and welcome email sending.
    """
    
    def __init__(
        self,
        config: dict,
        identity_service=None,
        notification_service=None,
    ):
        """
        Initialize email verification flow.
        
        Args:
            config: Identity flow config from identity.yaml
            identity_service: Injected identity service
            notification_service: Injected notification service
        """
        self.config = config
        self.identity_service = identity_service or get_identity_service()
        self.notification_service = notification_service or get_notification_service()
    
    async def execute(self, command: VerifyEmailCommand) -> VerifyEmailResult:
        """
        Execute email verification flow.
        
        Args:
            command: VerifyEmailCommand with token
        
        Returns:
            VerifyEmailResult with success/error
        """
        context = VerifyEmailContext(token=command.token)
        
        try:
            # Step 1: Verify email token
            logger.info(f"[Verify Email Flow] Step 1: Verifying email token")
            user = await self._verify_email_token_step(command, context)
            context.mark_email_verified(user.id, user.email)
            
            # Step 2: Send welcome email (optional)
            if self._should_send_welcome_email():
                logger.info(f"[Verify Email Flow] Step 2: Sending welcome email")
                await self._send_welcome_email_step(user, context)
            
            return VerifyEmailResult(
                success=True,
                identity_id=user.id,
                email=user.email,
                email_verified=context.email_verified,
                welcome_email_sent=context.welcome_email_sent,
                message="Email verified successfully",
            )
        
        except Exception as e:
            logger.error(f"[Verify Email Flow] Error: {str(e)}", exc_info=True)
            context.errors["verify_error"] = str(e)
            return VerifyEmailResult(
                success=False,
                error=str(e),
                message="Email verification failed",
            )
    
    async def _verify_email_token_step(self, command: VerifyEmailCommand, context: VerifyEmailContext):
        """
        Step 1: Verify email token.
        
        Args:
            command: VerifyEmailCommand
            context: VerifyEmailContext to update
        
        Returns:
            User entity from identity service
        
        Raises:
            Exception from identity service (invalid token, etc.)
        """
        from core.identity.dto.contracts import VerifyEmailCommand as IdentityVerifyEmailCommand
        
        verify_cmd = IdentityVerifyEmailCommand(token=command.token)
        result = await self.identity_service.verify_email(verify_cmd)
        
        return result.user  # Assuming result has user attribute
    
    async def _send_welcome_email_step(self, user, context: VerifyEmailContext):
        """
        Step 2: Send welcome email.
        
        Args:
            user: User entity from identity service
            context: VerifyEmailContext to update
        """
        from core.notification.dto.contracts import WelcomeEmailCommand
        
        welcome_cmd = WelcomeEmailCommand(
            recipient_email=user.email,
            recipient_name=getattr(user, "first_name", None),
            language="en",
            sender_key=self.config["templates"]["welcome_email"].get("sender_key"),
        )
        
        log = await self.notification_service.send_from_dto(
            welcome_cmd.to_send_notification_command()
        )
        
        if log.status.value != "SENT":
            logger.warning(f"[Verify Email Flow] Welcome email send failed: {log.error_message}")
            context.errors["welcome_email_failed"] = log.error_message
        else:
            logger.info(f"[Verify Email Flow] Welcome email sent to {user.email}")
            context.welcome_email_sent = True
    
    def _should_send_welcome_email(self) -> bool:
        """Check if welcome email should be sent."""
        return (
            self.config
            .get("flows", {})
            .get("verify_email", {})
            .get("features", {})
            .get("send_welcome_email", {})
            .get("enabled", False)
        )
