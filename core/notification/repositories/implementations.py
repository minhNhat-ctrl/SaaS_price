"""Django ORM implementations of notification repositories."""
from typing import List, Optional
from uuid import UUID

from ..domain.entities import NotificationSender, NotificationTemplate, NotificationLog
from ..domain.value_objects import Channel
from .interfaces import (
    NotificationSenderRepository,
    NotificationTemplateRepository,
    NotificationLogRepository,
)
from ..infrastructure.django_models import (
    NotificationSenderModel,
    NotificationTemplateModel,
    NotificationLogModel,
)


class DjangoNotificationSenderRepository(NotificationSenderRepository):
    """Django ORM implementation of NotificationSenderRepository."""
    
    def get_by_id(self, sender_id: UUID) -> Optional[NotificationSender]:
        """Get sender by ID."""
        try:
            model = NotificationSenderModel.objects.get(id=sender_id)
            return self._to_entity(model)
        except NotificationSenderModel.DoesNotExist:
            return None
    
    def get_by_key(self, sender_key: str) -> Optional[NotificationSender]:
        """Get sender by key (provider identifier)."""
        try:
            model = NotificationSenderModel.objects.get(sender_key=sender_key)
            return self._to_entity(model)
        except NotificationSenderModel.DoesNotExist:
            return None
    
    def get_active_by_channel(self, channel: Channel) -> Optional[NotificationSender]:
        """Get default active sender for channel."""
        # First try to get default
        model = NotificationSenderModel.objects.filter(
            channel=channel.value,
            is_active=True,
            is_default=True
        ).first()
        
        # If no default, get any active
        if not model:
            model = NotificationSenderModel.objects.filter(
                channel=channel.value,
                is_active=True
            ).first()
        
        return self._to_entity(model) if model else None
    
    def list_by_channel(self, channel: Channel) -> List[NotificationSender]:
        """List all senders for channel."""
        models = NotificationSenderModel.objects.filter(
            channel=channel.value,
            is_active=True
        ).order_by('-is_default', 'created_at')
        
        return [self._to_entity(m) for m in models]
    
    def save(self, sender: NotificationSender) -> NotificationSender:
        """Create or update sender."""
        model, created = NotificationSenderModel.objects.update_or_create(
            id=sender.id,
            defaults={
                'sender_key': sender.sender_key,
                'channel': sender.channel.value,
                'provider': sender.provider,
                'from_email': sender.from_email,
                'from_name': sender.from_name,
                'credentials_json': sender.credentials,
                'is_active': sender.is_active,
                'is_default': getattr(sender, 'is_default', False),
            }
        )
        return self._to_entity(model)
    
    @staticmethod
    def _to_entity(model: NotificationSenderModel) -> NotificationSender:
        """Convert model to domain entity."""
        return NotificationSender(
            id=model.id,
            sender_key=model.sender_key,
            channel=Channel(model.channel),
            provider=model.provider,
            from_email=model.from_email,
            from_name=model.from_name,
            credentials=model.credentials_json,
            is_active=model.is_active,
        )


class DjangoNotificationTemplateRepository(NotificationTemplateRepository):
    """Django ORM implementation of NotificationTemplateRepository."""
    
    def get(self, template_key: str, channel: Channel, language: str) -> Optional[NotificationTemplate]:
        """Get template by key, channel, language."""
        try:
            model = NotificationTemplateModel.objects.get(
                template_key=template_key,
                channel=channel.value,
                language=language
            )
            return self._to_entity(model)
        except NotificationTemplateModel.DoesNotExist:
            return None
    
    def get_or_default_language(self, template_key: str, channel: Channel, language: str) -> Optional[NotificationTemplate]:
        """Get template; fallback to default language (en) if not found."""
        # Try exact match
        model = NotificationTemplateModel.objects.filter(
            template_key=template_key,
            channel=channel.value,
            language=language
        ).first()
        
        # Fallback to English
        if not model:
            model = NotificationTemplateModel.objects.filter(
                template_key=template_key,
                channel=channel.value,
                language='en'
            ).first()
        
        return self._to_entity(model) if model else None
    
    def list_by_key(self, template_key: str) -> List[NotificationTemplate]:
        """List all language variants of a template."""
        models = NotificationTemplateModel.objects.filter(
            template_key=template_key,
            is_active=True
        ).order_by('language')
        
        return [self._to_entity(m) for m in models]
    
    def list_by_channel(self, channel: Channel) -> List[NotificationTemplate]:
        """List all templates for channel."""
        models = NotificationTemplateModel.objects.filter(
            channel=channel.value,
            is_active=True
        ).order_by('template_key', 'language')
        
        return [self._to_entity(m) for m in models]
    
    def save(self, template: NotificationTemplate) -> NotificationTemplate:
        """Create or update template."""
        model, created = NotificationTemplateModel.objects.update_or_create(
            id=template.id,
            defaults={
                'template_key': template.template_key,
                'channel': template.channel.value,
                'language': template.language,
                'subject': template.subject,
                'body': template.body,
                'is_active': template.is_active,
            }
        )
        return self._to_entity(model)
    
    def delete(self, template_id: UUID) -> bool:
        """Delete template."""
        result = NotificationTemplateModel.objects.filter(id=template_id).delete()
        return result[0] > 0
    
    @staticmethod
    def _to_entity(model: NotificationTemplateModel) -> NotificationTemplate:
        """Convert model to domain entity."""
        return NotificationTemplate(
            id=model.id,
            template_key=model.template_key,
            channel=Channel(model.channel),
            language=model.language,
            subject=model.subject,
            body=model.body,
            is_active=model.is_active,
        )


class DjangoNotificationLogRepository(NotificationLogRepository):
    """Django ORM implementation of NotificationLogRepository."""
    
    def save(self, log: NotificationLog) -> NotificationLog:
        """Save send log."""
        model = NotificationLogModel.objects.create(
            id=log.id,
            template_key=log.template_key,
            channel=log.channel.value,
            recipient=log.recipient,
            status=log.status.value,
            error_message=log.error_message or '',
            external_id=log.external_id,
            context_snapshot=log.context,
            sender_key=log.sender_key,
            sent_at=log.sent_at,
        )
        return self._to_entity(model)
    
    def get_by_id(self, log_id: UUID) -> Optional[NotificationLog]:
        """Get log by ID."""
        try:
            model = NotificationLogModel.objects.get(id=log_id)
            return self._to_entity(model)
        except NotificationLogModel.DoesNotExist:
            return None
    
    def list_by_template_key(self, template_key: str, limit: int = 100) -> List[NotificationLog]:
        """List recent send attempts for template."""
        models = NotificationLogModel.objects.filter(
            template_key=template_key
        ).order_by('-created_at')[:limit]
        
        return [self._to_entity(m) for m in models]
    
    @staticmethod
    def _to_entity(model: NotificationLogModel) -> NotificationLog:
        """Convert model to domain entity."""
        from ..domain.value_objects import SendStatus
        
        return NotificationLog(
            id=model.id,
            template_key=model.template_key,
            channel=Channel(model.channel),
            recipient=model.recipient,
            status=SendStatus(model.status),
            error_message=model.error_message,
            external_id=model.external_id,
            context=model.context_snapshot,
            sender_key=model.sender_key,
            sent_at=model.sent_at,
            created_at=model.created_at,
        )
