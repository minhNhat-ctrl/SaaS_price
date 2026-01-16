"""Notification API views.

IMPORTANT: This API layer is MINIMAL and internal-only.

Responsibility Boundaries:
- ✗ NO CRUD endpoints for Senders or Templates (only Django admin manages these)
- ✗ NO public API for sending notifications (only application layer can send)
- ✓ Read-only audit trail for notification logs
- ✓ Internal send endpoint for application layer calls
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated

from ..infrastructure.django_models import NotificationLogModel
from .serializers import (
    NotificationLogSerializer,
    NotificationLogDetailSerializer,
    SendNotificationSerializer,
)
from ..services.use_cases import NotificationService
from ..repositories.implementations import (
    DjangoNotificationSenderRepository,
    DjangoNotificationTemplateRepository,
    DjangoNotificationLogRepository,
)
from ..domain.value_objects import SendCommand, Channel
from ..domain.exceptions import (
    TemplateNotFoundError,
    SenderNotFoundError,
    TemplateRenderError,
    NotificationSendError,
)


class NotificationLogViewSet(ReadOnlyModelViewSet):
    """API for viewing notification logs (read-only audit trail).
    
    Admin/Dashboard use case: view send history, debug failures, track delivery.
    """
    
    queryset = NotificationLogModel.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Use detail serializer for detail view."""
        if self.action == 'retrieve':
            return NotificationLogDetailSerializer
        return NotificationLogSerializer
    
    def get_queryset(self):
        """Filter by various criteria."""
        queryset = super().get_queryset()
        
        if template_key := self.request.query_params.get('template_key'):
            queryset = queryset.filter(template_key=template_key)
        
        if channel := self.request.query_params.get('channel'):
            queryset = queryset.filter(channel=channel)
        
        if status_filter := self.request.query_params.get('status'):
            queryset = queryset.filter(status=status_filter)
        
        if recipient := self.request.query_params.get('recipient'):
            queryset = queryset.filter(recipient__icontains=recipient)
        
        return queryset.order_by('-created_at')


class SendNotificationEndpoint:
    """
    Internal endpoint for sending notifications.
    
    ⚠️  IMPORTANT:
    - This is called ONLY by the Application layer (never directly by external API clients)
    - The Application layer decides WHAT to send and WHEN to send
    - This endpoint executes the send command (renders template, calls provider)
    
    Example flow:
    1. Application layer (signup flow): decides to send welcome email
    2. Application → calls notification.send(SendCommand(...))
    3. Notification service → queries repository → renders template → sends via provider
    4. Logs result to NotificationLog
    
    TODO: Once Application layer exists, integrate this endpoint there.
    """
    
    def __init__(self):
        self.service = NotificationService(
            sender_repo=DjangoNotificationSenderRepository(),
            template_repo=DjangoNotificationTemplateRepository(),
            log_repo=DjangoNotificationLogRepository(),
        )
    
    def post(self, request):
        """
        Send a notification (internal use only).
        
        Request body:
        {
            "template_key": "welcome_email",
            "channel": "EMAIL",
            "recipient": "user@example.com",
            "language": "en",
            "context": {
                "user_name": "John",
                "activation_url": "https://..."
            },
            "sender_key": "sendgrid_primary"  # optional
        }
        
        Returns:
        {
            "success": true,
            "message": "Notification sent successfully",
            "log_id": "uuid",
            "external_id": "provider_message_id"
        }
        """
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            command = SendCommand(
                template_key=serializer.validated_data['template_key'],
                channel=Channel(serializer.validated_data['channel']),
                recipient=serializer.validated_data['recipient'],
                language=serializer.validated_data.get('language', 'en'),
                context=serializer.validated_data.get('context', {}),
                sender_key=serializer.validated_data.get('sender_key'),
            )
            
            log = self.service.send(command)
            
            return Response(
                {
                    'success': True,
                    'message': 'Notification sent successfully',
                    'log_id': str(log.id),
                    'external_id': log.external_id,
                },
                status=status.HTTP_200_OK
            )
        
        except TemplateNotFoundError as e:
            return Response(
                {'error': str(e), 'code': 'TEMPLATE_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        except SenderNotFoundError as e:
            return Response(
                {'error': str(e), 'code': 'SENDER_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        except (TemplateRenderError, NotificationSendError) as e:
            return Response(
                {'error': str(e), 'code': 'SEND_FAILED'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Unexpected error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
