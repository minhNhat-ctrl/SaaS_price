"""
Password Reset Confirmation Flow Orchestrator.

Multi-step flow:
1. Confirm password reset with token (core/identity)
2. Send password reset confirmation email (core/notification)
"""
import logging
from asgiref.sync import sync_to_async

from application.dto.identity import (
    PasswordResetConfirmCommand,
    PasswordResetConfirmContext,
    PasswordResetConfirmResult,
)
from core.identity.services.providers import get_identity_service
from core.notification.services.providers import get_notification_service

logger = logging.getLogger(__name__)


class PasswordResetConfirmFlow:
    """
    Password reset confirmation flow orchestrator.
    
    Orchestrates password reset token validation and confirmation.
    """
    
    def __init__(
        self,
        config: dict,
        identity_service=None,
        notification_service=None,
    ):
        """
        Initialize password reset confirmation flow.
        
        Args:
            config: Identity flow config from identity.yaml
            identity_service: Injected identity service
            notification_service: Injected notification service
        """
        self.config = config
        self.identity_service = identity_service or get_identity_service()
        self.notification_service = notification_service or get_notification_service()
    
    async def execute(self, command: PasswordResetConfirmCommand) -> PasswordResetConfirmResult:
        """
        Execute password reset confirmation flow.
        
        Args:
            command: PasswordResetConfirmCommand with token, new_password
        
        Returns:
            PasswordResetConfirmResult with success/error
        """
        context = PasswordResetConfirmContext(token=command.token)
        
        try:
            # Step 1: Confirm password reset
            logger.info(f"[Password Reset Confirm Flow] Step 1: Confirming password reset")
            identity = await self._confirm_password_reset_step(command, context)
            context.mark_password_changed(getattr(identity, "id", None), getattr(identity, "email", None))
            
            # Step 2: Send confirmation email (optional)
            if self._should_send_confirmation_email():
                logger.info(f"[Password Reset Confirm Flow] Step 2: Sending confirmation email")
                await self._send_confirmation_email_step(identity, context)
            
            return PasswordResetConfirmResult(
                success=True,
                identity_id=getattr(identity, "id", None),
                email=getattr(identity, "email", None),
                confirmation_email_sent=context.confirmation_email_sent,
                message="Password reset successfully",
            )
        
        except Exception as e:
            logger.error(f"[Password Reset Confirm Flow] Error: {str(e)}", exc_info=True)
            context.errors["confirm_error"] = str(e)
            return PasswordResetConfirmResult(
                success=False,
                error=str(e),
                message="Password reset confirmation failed",
            )
    
    async def _confirm_password_reset_step(self, command: PasswordResetConfirmCommand, context: PasswordResetConfirmContext):
        """
        Step 1: Confirm password reset with token.
        
        Args:
            command: PasswordResetConfirmCommand
            context: PasswordResetConfirmContext to update
        
        Returns:
            Result with identity_id, email
        
        Raises:
            Exception from identity service (invalid token, etc.)
        """
        # IdentityService.reset_password_with_token signature: (token: str, new_password: str) -> UserIdentity
        identity = await self.identity_service.reset_password_with_token(command.token, command.new_password)
        return identity
    
    async def _send_confirmation_email_step(self, identity, context: PasswordResetConfirmContext):
        """
        Step 2: Send password reset confirmation email.
        
        Args:
            reset_result: Result from _confirm_password_reset_step
            context: PasswordResetConfirmContext to update
        """
        from core.notification.dto.contracts import SendNotificationCommand
        from core.notification.domain.value_objects import Channel
        
        # Send generic notification (template_key: password_reset_confirmation)
        template_cfg = self.config["templates"].get("password_reset_confirmation", {})
        cmd = SendNotificationCommand(
            template_key=template_cfg.get("template_key", "password_reset_confirmation"),
            channel=Channel.EMAIL,
            recipient=identity.email,
            language=template_cfg.get("language", "en"),
            sender_key=template_cfg.get("sender_key"),
            context={"email": identity.email},
        )
        
        try:
            log = await sync_to_async(self.notification_service.send_from_dto)(cmd)
            
            if log.status.value != "SENT":
                logger.warning(f"[Password Reset Confirm Flow] Confirmation email send failed: {log.error_message}")
                context.errors["confirmation_email_failed"] = log.error_message
            else:
                logger.info(f"[Password Reset Confirm Flow] Confirmation email sent to {reset_result.email}")
                context.confirmation_email_sent = True
        except Exception as exc:
            logger.warning(f"[Password Reset Confirm Flow] Confirmation email send exception: {exc}")
            context.errors["confirmation_email_failed"] = str(exc)
    
    def _should_send_confirmation_email(self) -> bool:
        """Check if confirmation email should be sent."""
        return (
            self.config
            .get("flows", {})
            .get("password_reset_confirm", {})
            .get("send_confirmation_email", True)
        )
