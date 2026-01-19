"""Create product API endpoint (placeholder)."""
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class CreateProductView(APIView):
    """
    Create product endpoint.
    
    POST /api/business/create-product/
    
    TODO: Implement product creation flow.
    """
    
    def post(self, request: Request) -> Response:
        """Create a product."""
        return Response(
            {
                'success': False,
                'data': None,
                'error': {'code': 'NOT_IMPLEMENTED', 'detail': 'Create product endpoint not yet implemented'},
                'message': 'Feature coming soon',
            },
            status=501,
        )
