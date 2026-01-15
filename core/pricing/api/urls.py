from django.urls import path

from core.pricing.api.views import PlanCatalogAPIView
from core.pricing.services.use_cases import PlanCatalogService


def build_urls(service: PlanCatalogService):
    """Factory returning URL patterns with injected service instance."""

    return [
        path("plans/", PlanCatalogAPIView.as_view(service=service), name="pricing-plan-list"),
    ]
