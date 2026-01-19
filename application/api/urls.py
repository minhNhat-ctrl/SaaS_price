"""Application API root URLs."""
from django.urls import path, include


urlpatterns = [
    path('identity/', include('application.api.identity.urls')),
    path('provisioning/', include('application.api.provisioning.urls')),
    path('business/', include('application.api.business.urls')),
]
