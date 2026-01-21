"""Password reset confirmation API endpoint."""
from asgiref.sync import async_to_sync
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from application.dto.identity import PasswordResetConfirmCommand
from application.services.identity_flows import get_password_reset_confirm_flow


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Validate password reset confirmation payload."""

    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8, write_only=True)
    new_password_confirm = serializers.CharField(required=True, min_length=8, write_only=True)

    def validate(self, attrs):
        if attrs.get("new_password") != attrs.get("new_password_confirm"):
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        return attrs

    def to_command(self) -> PasswordResetConfirmCommand:
        data = self.validated_data
        return PasswordResetConfirmCommand(
            token=data["token"],
            new_password=data["new_password"],
            new_password_confirm=data["new_password_confirm"],
        )


class PasswordResetConfirmView(APIView):
    """Confirm password reset using token and set new password.

    POST /api/identity/password-reset-confirm/
    Body: {"token": "...", "new_password": "...", "new_password_confirm": "..."}
    """

    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "data": None,
                    "error": {"code": "VALIDATION_ERROR", "detail": serializer.errors},
                    "message": "Validation failed",
                },
                status=HTTP_400_BAD_REQUEST,
            )

        command = serializer.to_command()
        flow = get_password_reset_confirm_flow()

        try:
            result = async_to_sync(flow.execute)(command)

            if not result.success:
                return Response(
                    {
                        "success": False,
                        "data": None,
                        "error": {"code": "PASSWORD_RESET_CONFIRM_FAILED", "detail": result.error or result.message},
                        "message": result.message or "Password reset confirmation failed",
                    },
                    status=HTTP_400_BAD_REQUEST,
                )

            data = {
                "identity_id": str(result.identity_id) if result.identity_id else None,
                "email": result.email,
                "confirmation_email_sent": result.confirmation_email_sent,
            }

            return Response(
                {
                    "success": True,
                    "data": data,
                    "error": None,
                    "message": result.message or "Password reset successfully",
                },
                status=HTTP_200_OK,
            )

        except Exception as exc:  # pragma: no cover
            return Response(
                {
                    "success": False,
                    "data": None,
                    "error": {"code": exc.__class__.__name__, "detail": str(exc)},
                    "message": "Password reset confirmation failed",
                },
                status=HTTP_400_BAD_REQUEST,
            )
