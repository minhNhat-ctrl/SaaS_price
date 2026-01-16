"""Notification API serializers.

⚠️  IMPORTANT: Minimal serializers - no CRUD serializers for Senders/Templates.

Only exposed serializers:
- NotificationLogSerializer (read-only audit trail)
- SendNotificationSerializer (internal send command)

Sender & Template management: Django admin only.
"""
from rest_framework import serializers

from ..infrastructure.django_models import NotificationLogModel
from ..domain.value_objects import Channel


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for NotificationLog (read-only audit trail)."""
    
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = NotificationLogModel
        fields = [
            'id',
            'template_key',
            'channel',
            'channel_display',
            'recipient',
            'status',
            'status_display',
            'error_message',
            'external_id',
            'sender_key',
            'sent_at',
            'created_at',
        ]
        read_only_fields = fields


class NotificationLogDetailSerializer(NotificationLogSerializer):
    """Detailed serializer for NotificationLog (includes context snapshot)."""
    
    class Meta(NotificationLogSerializer.Meta):
        fields = NotificationLogSerializer.Meta.fields + ['context_snapshot']


class SendNotificationSerializer(serializers.Serializer):
    """Serializer for SendCommand (API input for sending notifications)."""
    
    template_key = serializers.CharField(max_length=255)
    channel = serializers.ChoiceField(choices=['EMAIL', 'SMS', 'PUSH', 'WEBHOOK'])
    recipient = serializers.CharField(max_length=500)
    language = serializers.CharField(max_length=10, default='en')
    context = serializers.JSONField(default=dict)
    sender_key = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    def validate_channel(self, value):
        """Validate channel is a valid Channel."""
        if value not in ['EMAIL', 'SMS', 'PUSH', 'WEBHOOK']:
            raise serializers.ValidationError(f"Invalid channel: {value}")
        return value
