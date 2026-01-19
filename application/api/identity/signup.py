"""Signup API endpoint."""
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from application.dto.identity import SignupCommand
from application.flows.provisioning.tenant_onboarding_flow import TenantOnboardingFlow
from application.api.provisioning.providers import get_onboarding_flow


class SignupRequestSerializer(serializers.Serializer):
    """Validates and transforms signup request."""
    
    email = serializers.EmailField(required=True, help_text="User email address")
    password = serializers.CharField(required=True, min_length=8, write_only=True, help_text="Password (min 8 chars)")
    source = serializers.CharField(required=False, default="web", help_text="Signup source")
    
    def to_command(self) -> SignupCommand:
        """Transform to SignupCommand DTO."""
        return SignupCommand(
            email=self.validated_data['email'],
            password=self.validated_data['password'],
            source=self.validated_data.get('source', 'web'),
        )


class SignupView(APIView):
    """
    User signup endpoint - initiates provisioning flow.
    
    POST /api/identity/signup/
    """
    
    def post(self, request: Request) -> Response:
        """Process signup request."""
        serializer = SignupRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'data': None,
                    'error': {'code': 'VALIDATION_ERROR', 'detail': serializer.errors},
                    'message': 'Validation failed',
                },
                status=HTTP_400_BAD_REQUEST,
            )
        
        command = serializer.to_command()
        
        try:
            flow = get_onboarding_flow()
            if not flow:
                return Response(
                    {'success': False, 'data': None, 'error': {'code': 'FLOW_NOT_CONFIGURED', 'detail': 'Onboarding flow not initialized'}, 'message': 'Internal server error'},
                    status=500,
                )
            
            context = flow.run(command)
            
            return Response(
                {
                    'success': True,
                    'data': {
                        'user_id': context.user_id,
                        'tenant_id': context.tenant_id,
                        'plan_code': context.plan_code,
                        'subscription_status': context.subscription_status,
                        'quote_id': context.quote_id,
                        'requires_payment': context.requires_payment,
                        'metadata': context.metadata,
                    },
                    'error': None,
                    'message': 'Provisioning completed successfully',
                },
                status=HTTP_201_CREATED,
            )
        
        except Exception as exc:
            return Response(
                {
                    'success': False,
                    'data': None,
                    'error': {'code': exc.__class__.__name__, 'detail': str(exc)},
                    'message': f'Provisioning failed: {str(exc)}',
                },
                status=HTTP_400_BAD_REQUEST,
            )
