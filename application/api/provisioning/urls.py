"""Provisioning API URLs."""
from django.urls import path

from .create_tenant import CreateTenantView


urlpatterns = [
    path('create-tenant/', CreateTenantView.as_view(), name='provisioning-create-tenant'),
]
