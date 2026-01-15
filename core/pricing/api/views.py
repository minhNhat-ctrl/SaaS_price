from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pricing.api.serializers import PlanSerializer
from core.pricing.services.use_cases import PlanCatalogService


class PlanCatalogAPIView(APIView):
    """Read-only view for plan catalog; expects PlanCatalogService injection."""

    service: PlanCatalogService

    def __init__(self, *args, **kwargs):
        self.service = kwargs.pop("service")
        super().__init__(*args, **kwargs)

    def get(self, request):
        plans = self.service.list_active_plans()
        data = [PlanSerializer.from_service(plan) for plan in plans]
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
