"""Create tenant API endpoint (placeholder)."""
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class CreateTenantView(APIView):
    """
    Create tenant endpoint (manual tenant creation outside provisioning flow).
    
    POST /api/provisioning/create-tenant/
    
    TODO: Implement standalone tenant creation.
    """
    
    def post(self, request: Request) -> Response:
        """Create a tenant."""
        return Response(
            {
                'success': False,
                'data': None,
                'error': {'code': 'NOT_IMPLEMENTED', 'detail': 'Create tenant endpoint not yet implemented'},
                'message': 'Feature coming soon',
            },
            status=501,
        )
