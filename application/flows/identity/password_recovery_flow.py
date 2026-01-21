"""
Password Recovery Flow Orchestrator.

Multi-step flow:
1. Request password reset (core/identity)
2. Send password reset email (core/notification)
"""
import logging

from application.dto.identity import (
    PasswordRecoveryCommand,
    PasswordRecoveryContext,
    PasswordRecoveryResult,
)
from core.identity.services.providers import get_identity_service
from core.notification.services.providers import get_notification_service

logger = logging.getLogger(__name__)


class PasswordRecoveryFlow:
    """
    Password recovery flow orchestrator.
    
    Orchestrates password reset token generation and email sending.
    """
    
    def __init__(
        self,
        config: dict,
        identity_service=None,
        notification_service=None,
    ):
        """
        Initialize password recovery flow.
        
        Args:
            config: Identity flow config from identity.yaml
            identity_service: Injected identity service
            notification_service: Injected notification service
        """
        self.config = config
        self.identity_service = identity_service or get_identity_service()
        self.notification_service = notification_service or get_notification_service()
    
    async def execute(self, command: PasswordRecoveryCommand) -> PasswordRecoveryResult:
        """
        Execute password recovery flow.
        
        Args:
            command: PasswordRecoveryCommand with email
        
        Returns:
            PasswordRecoveryResult with success/error
        """
        context = PasswordRecoveryContext(email=command.email)
        
        try:
            # Step 1: Request password reset token
            logger.info(f"[Password Recovery Flow] Step 1: Requesting reset token for {command.email}")
            result = await self._request_password_reset_step(command, context)
            context.mark_reset_requested(result.reset_token)
            
            # Step 2: Send password reset email
            logger.info(f"[Password Recovery Flow] Step 2: Sending reset email")
            await self._send_password_reset_email_step(command, result, context)
            
            return PasswordRecoveryResult(
                success=True,
                email=command.email,
                reset_email_sent=context.reset_email_sent,
                message="Password reset email sent",
            )
        
        except Exception as e:
            logger.error(f"[Password Recovery Flow] Error: {str(e)}", exc_info=True)
            context.errors["recovery_error"] = str(e)
            return PasswordRecoveryResult(
                success=False,
                email=command.email,
                error=str(e),
                message="Password recovery failed",
            )
    
    async def _request_password_reset_step(self, command: PasswordRecoveryCommand, context: PasswordRecoveryContext):
        """
        Step 1: Request password reset token.
        
        Args:
            command: PasswordRecoveryCommand
            context: PasswordRecoveryContext to update
        
        Returns:
            Result with reset_token
        
        Raises:
            Exception from identity service
        """
        from core.identity.dto.contracts import PasswordResetRequestCommand
        
        request_cmd = PasswordResetRequestCommand(email=command.email)
        result = await self.identity_service.request_password_reset(request_cmd)
        
        return result
    
    async def _send_password_reset_email_step(self, command: PasswordRecoveryCommand, reset_result, context: PasswordRecoveryContext):
        """
        Step 2: Send password reset email.
        
        Args:
            command: PasswordRecoveryCommand
            reset_result: Result from request_password_reset_step
            context: PasswordRecoveryContext to update
        """
        from core.notification.dto.contracts import PasswordResetEmailCommand
        
        frontend_url = (
            self.config
            .get("frontend", {})
            .get("password_reset_url", "")
        )
        
        reset_cmd = PasswordResetEmailCommand(
            recipient_email=command.email,
            reset_token=reset_result.reset_token,
            reset_url=f"{frontend_url}?token={reset_result.reset_token}",
            language="en",
            sender_key=self.config["templates"]["password_reset"].get("sender_key"),
        )
        
        log = await self.notification_service.send_from_dto(
            reset_cmd.to_send_notification_command()
        )
        
        if log.status.value != "SENT":
            logger.warning(f"[Password Recovery Flow] Reset email send failed: {log.error_message}")
            context.errors["reset_email_failed"] = log.error_message
        else:
            logger.info(f"[Password Recovery Flow] Reset email sent to {command.email}")
