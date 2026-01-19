"""URL routing for provisioning flow HTTP API."""
from django.urls import path

from .views import ProvisioningSignupView, ProvisioningStatusView

app_name = 'provisioning'

urlpatterns = [
    # Signup endpoint - initiate provisioning flow
    path(
        'signup/',
        ProvisioningSignupView.as_view(),
        name='signup'
    ),
    # Status endpoint - check provisioning status
    path(
        'status/<str:user_id>/',
        ProvisioningStatusView.as_view(),
        name='status'
    ),
]
