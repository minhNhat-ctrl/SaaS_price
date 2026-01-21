"""Verify email API endpoint wired to identity verify email flow."""
from asgiref.sync import async_to_sync
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from application.dto.identity import VerifyEmailCommand
from application.services.identity_flows import get_verify_email_flow


class VerifyEmailRequestSerializer(serializers.Serializer):
    """Validate verification token from email link."""

    token = serializers.CharField(required=True)

    def to_command(self) -> VerifyEmailCommand:
        data = self.validated_data
        return VerifyEmailCommand(token=data["token"])


class VerifyEmailView(APIView):
    """Email verification endpoint.

    POST /api/identity/verify-email/
    Body: {"token": "<token from email link>"}
    """

    def post(self, request: Request) -> Response:
        serializer = VerifyEmailRequestSerializer(data=request.data)
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
        flow = get_verify_email_flow()

        try:
            result = async_to_sync(flow.execute)(command)

            if not result.success:
                return Response(
                    {
                        "success": False,
                        "data": None,
                        "error": {"code": "VERIFY_EMAIL_FAILED", "detail": result.error or result.message},
                        "message": result.message or "Email verification failed",
                    },
                    status=HTTP_400_BAD_REQUEST,
                )

            data = {
                "identity_id": str(result.identity_id) if result.identity_id else None,
                "email": result.email,
                "email_verified": result.email_verified,
                "welcome_email_sent": result.welcome_email_sent,
            }

            return Response(
                {
                    "success": True,
                    "data": data,
                    "error": None,
                    "message": result.message or "Email verified successfully",
                },
                status=HTTP_200_OK,
            )

        except Exception as exc:  # pragma: no cover
            return Response(
                {
                    "success": False,
                    "data": None,
                    "error": {"code": exc.__class__.__name__, "detail": str(exc)},
                    "message": "Email verification failed",
                },
                status=HTTP_400_BAD_REQUEST,
            )
