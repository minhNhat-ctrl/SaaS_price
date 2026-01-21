"""Signin API endpoint wired to identity signin flow."""
from asgiref.sync import async_to_sync
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from application.dto.identity import SigninCommand
from application.services.identity_flows import get_signin_flow


class SigninRequestSerializer(serializers.Serializer):
    """Validate and transform signin request for identity flow."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def to_command(self) -> SigninCommand:
        data = self.validated_data
        return SigninCommand(email=data["email"], password=data["password"])


class SigninView(APIView):
    """User signin endpoint.

    POST /api/identity/signin/
    """

    def post(self, request: Request) -> Response:
        serializer = SigninRequestSerializer(data=request.data)
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
        flow = get_signin_flow()

        try:
            result = async_to_sync(flow.execute)(command)

            if not result.success:
                return Response(
                    {
                        "success": False,
                        "data": None,
                        "error": {"code": "SIGNIN_FAILED", "detail": result.error or result.message},
                        "message": result.message or "Signin failed",
                    },
                    status=HTTP_400_BAD_REQUEST,
                )

            data = {
                "identity_id": str(result.identity_id) if result.identity_id else None,
                "session_token": result.session_token,
            }

            return Response(
                {
                    "success": True,
                    "data": data,
                    "error": None,
                    "message": result.message or "Signin successful",
                },
                status=HTTP_200_OK,
            )

        except Exception as exc:  # pragma: no cover
            return Response(
                {
                    "success": False,
                    "data": None,
                    "error": {"code": exc.__class__.__name__, "detail": str(exc)},
                    "message": "Signin failed",
                },
                status=HTTP_400_BAD_REQUEST,
            )
