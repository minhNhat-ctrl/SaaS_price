"""Notification API URL routing.

⚠️  IMPORTANT: Minimal API - no CRUD for senders/templates (only Django admin).

Exposed endpoints:
- GET /api/notifications/logs/ - Read-only audit trail
- GET /api/notifications/logs/{id}/ - Log detail

Internal endpoint (called by Application layer):
- POST /api/notifications/send/ - Send notification (internal only)
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationLogViewSet,
    SendNotificationEndpoint,
)

app_name = 'notification'

router = DefaultRouter()
router.register(r'logs', NotificationLogViewSet, basename='log')

# Instantiate internal send endpoint
send_endpoint = SendNotificationEndpoint()

urlpatterns = [
    path('', include(router.urls)),
    path('send/', send_endpoint.post, name='send'),  # Internal: called by application layer only
]
