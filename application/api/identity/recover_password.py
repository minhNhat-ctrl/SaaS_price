"""Password recovery API endpoint wired to password recovery flow."""
from asgiref.sync import async_to_sync
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from application.dto.identity import PasswordRecoveryCommand
from application.services.identity_flows import get_password_recovery_flow


class PasswordRecoveryRequestSerializer(serializers.Serializer):
    """Validate password recovery request."""

    email = serializers.EmailField(required=True)

    def to_command(self) -> PasswordRecoveryCommand:
        return PasswordRecoveryCommand(email=self.validated_data["email"])


class RecoverPasswordView(APIView):
    """Password recovery endpoint.

    POST /api/identity/password-recovery/
    """

    def post(self, request: Request) -> Response:
        serializer = PasswordRecoveryRequestSerializer(data=request.data)
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
        flow = get_password_recovery_flow()

        try:
            result = async_to_sync(flow.execute)(command)

            if not result.success:
                return Response(
                    {
                        "success": False,
                        "data": None,
                        "error": {"code": "PASSWORD_RECOVERY_FAILED", "detail": result.error or result.message},
                        "message": result.message or "Password recovery failed",
                    },
                    status=HTTP_400_BAD_REQUEST,
                )

            return Response(
                {
                    "success": True,
                    "data": {"email": result.email, "reset_email_sent": result.reset_email_sent},
                    "error": None,
                    "message": result.message or "Password reset email sent",
                },
                status=HTTP_200_OK,
            )

        except Exception as exc:  # pragma: no cover
            return Response(
                {
                    "success": False,
                    "data": None,
                    "error": {"code": exc.__class__.__name__, "detail": str(exc)},
                    "message": "Password recovery failed",
                },
                status=HTTP_400_BAD_REQUEST,
            )
