"""Views for provisioning flow HTTP API."""
from typing import Optional

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from application.dto.provisioning import SignupCommand, ProvisioningContext
from application.orchestrators.provisioning import ProvisioningFlowOrchestrator
from application.interfaces.http.provisioning.providers import (
    get_provisioning_orchestrator,
)
from .serializers import (
    SignupRequestSerializer,
    ProvisioningContextResponseSerializer,
)


class ProvisioningSignupView(APIView):
    """
    Initiate provisioning flow starting from signup.
    
    POST /api/provisioning/signup/
    
    Request body:
        {
            "email": "user@example.com",
            "password": "securepassword123",
            "source": "web"  # optional
        }
    
    Response (201 Created):
        {
            "success": true,
            "data": {
                "user_id": "uuid",
                "tenant_id": "uuid",
                "plan_code": "starter",
                "subscription_status": "trial",
                "requires_payment": false,
                "metadata": {...}
            },
            "error": null,
            "message": "Provisioning completed successfully"
        }
    """

    orchestrator: Optional[ProvisioningFlowOrchestrator] = None

    def __init__(self, orchestrator: Optional[ProvisioningFlowOrchestrator] = None, **kwargs) -> None:
        """Initialize with provisioning orchestrator (can be injected)."""
        super().__init__(**kwargs)
        if orchestrator:
            self.orchestrator = orchestrator

    def post(self, request: Request) -> Response:
        """
        Execute provisioning flow starting from signup.
        
        Steps executed (subject to toggle):
        1. Signup (create user account)
        2. Verify Email (send & verify email)
        3. Signin (establish session)
        4. Create Tenant (provision tenant)
        5. Resolve Subscription (initialize subscription)
        6. Assign Plan (select plan)
        7. Quote Payment (if required, create payment quote)
        8. Activate Tenant (finalize activation)
        """
        # Validate request
        serializer = SignupRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'data': None,
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'detail': serializer.errors,
                    },
                    'message': 'Validation failed',
                },
                status=HTTP_400_BAD_REQUEST,
            )

        # Transform to DTO
        command: SignupCommand = serializer.to_command()

        try:
            # Run orchestrator (injected at view initialization)
            if not self.orchestrator:
                # Try to resolve orchestrator from global provider
                self.orchestrator = get_provisioning_orchestrator()
                if not self.orchestrator:
                    return Response(
                        {
                            'success': False,
                            'data': None,
                            'error': {
                                'code': 'ORCHESTRATOR_NOT_CONFIGURED',
                                'detail': 'Provisioning orchestrator not initialized',
                            },
                            'message': 'Internal server error',
                        },
                        status=500,
                    )

            context: ProvisioningContext = self.orchestrator.run(command)

            # Transform context to response
            response_data = ProvisioningContextResponseSerializer.from_context(context)

            return Response(
                {
                    'success': True,
                    'data': response_data,
                    'error': None,
                    'message': 'Provisioning completed successfully',
                },
                status=HTTP_201_CREATED,
            )

        except Exception as exc:
            # Handle domain/service exceptions
            return Response(
                {
                    'success': False,
                    'data': None,
                    'error': {
                        'code': exc.__class__.__name__,
                        'detail': str(exc),
                    },
                    'message': f'Provisioning failed: {str(exc)}',
                },
                status=HTTP_400_BAD_REQUEST,
            )


class ProvisioningStatusView(APIView):
    """
    Check provisioning status (placeholder for future use).
    
    GET /api/provisioning/status/{user_id}/
    
    Returns provisioning context snapshot for a user.
    """

    def get(self, request: Request, user_id: str) -> Response:
        """
        Retrieve provisioning status for a user.
        
        TODO: Implement with context storage/retrieval from DB.
        """
        return Response(
            {
                'success': False,
                'data': None,
                'error': {
                    'code': 'NOT_IMPLEMENTED',
                    'detail': 'Provisioning status endpoint not yet implemented',
                },
                'message': 'Feature coming soon',
            },
            status=501,
        )
