"""Signup API endpoint wired to identity signup flow."""
from asgiref.sync import async_to_sync
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from application.dto.identity import SignupCommand
from application.services.identity_flows import get_signup_flow


class SignupRequestSerializer(serializers.Serializer):
    """Validate and transform signup request for identity flow."""

    email = serializers.EmailField(required=True, help_text="User email address")
    password = serializers.CharField(required=True, min_length=8, write_only=True, help_text="Password (min 8 chars)")
    password_confirm = serializers.CharField(required=False, write_only=True, help_text="Password confirmation")
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    def to_command(self) -> SignupCommand:
        """Transform to SignupCommand DTO for flow layer."""
        data = self.validated_data
        password = data["password"]
        password_confirm = data.get("password_confirm") or password

        return SignupCommand(
            email=data["email"],
            password=password,
            password_confirm=password_confirm,
            first_name=data.get("first_name") or None,
            last_name=data.get("last_name") or None,
        )


class SignupView(APIView):
    """User signup endpoint.

    POST /api/identity/signup/
    """

    def post(self, request: Request) -> Response:
        serializer = SignupRequestSerializer(data=request.data)
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
        flow = get_signup_flow()

        try:
            # Execute async flow from sync APIView
            result = async_to_sync(flow.execute)(command)

            if not result.success:
                return Response(
                    {
                        "success": False,
                        "data": None,
                        "error": {"code": "SIGNUP_FAILED", "detail": result.error or result.message},
                        "message": result.message or "Signup failed",
                    },
                    status=HTTP_400_BAD_REQUEST,
                )

            # Map to frontend SignupResponse shape as much as possible
            data = {
                "user_id": str(result.identity_id) if result.identity_id else "",
                "email": result.email,
                "metadata": {
                    "verify_required": result.email_verification_required,
                },
            }

            return Response(
                {
                    "success": True,
                    "data": data,
                    "error": None,
                    "message": result.message or "Signup successful",
                },
                status=HTTP_201_CREATED,
            )

        except Exception as exc:  # pragma: no cover - generic safeguard
            return Response(
                {
                    "success": False,
                    "data": None,
                    "error": {"code": exc.__class__.__name__, "detail": str(exc)},
                    "message": "Signup failed",
                },
                status=HTTP_400_BAD_REQUEST,
            )
