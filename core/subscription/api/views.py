from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.subscription.api.serializers import SubscriptionSerializer
from core.subscription.domain.exceptions import SubscriptionNotFoundError
from core.subscription.dto import ActiveSubscriptionQuery
from core.subscription.services.use_cases import SubscriptionManagementService


class CurrentTenantSubscriptionAPIView(APIView):
    """Read current tenant's active subscription. Expects tenant context from middleware."""

    service: SubscriptionManagementService

    def __init__(self, *args, **kwargs):
        self.service = kwargs.pop("service")
        super().__init__(*args, **kwargs)

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        if not tenant_id:
            return Response(
                {"success": False, "error": "No tenant context"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            dto = self.service.get_active_subscription(ActiveSubscriptionQuery(tenant_id=tenant_id))
            data = SubscriptionSerializer.from_dto(dto)
            return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
        except SubscriptionNotFoundError:
            return Response(
                {"success": False, "error": "No active subscription"},
                status=status.HTTP_404_NOT_FOUND,
            )
