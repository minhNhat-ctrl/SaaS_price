from django.urls import path

from core.subscription.api.views import CurrentTenantSubscriptionAPIView
from core.subscription.services.use_cases import SubscriptionManagementService


def build_urls(service: SubscriptionManagementService):
    """Factory returning URL patterns with injected service instance."""

    return [
        path(
            "current/",
            CurrentTenantSubscriptionAPIView.as_view(service=service),
            name="subscription-current",
        ),
    ]
