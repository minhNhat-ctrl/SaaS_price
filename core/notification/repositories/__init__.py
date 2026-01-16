"""Notification repository interfaces."""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..domain.entities import NotificationSender, NotificationTemplate, NotificationLog
from ..domain.value_objects import Channel


class NotificationSenderRepository(ABC):
    """Repository for notification senders."""
    
    @abstractmethod
    def get_by_id(self, sender_id: UUID) -> Optional[NotificationSender]:
        """Get sender by ID."""
        pass
    
    @abstractmethod
    def get_by_key(self, sender_key: str) -> Optional[NotificationSender]:
        """Get sender by key (provider identifier)."""
        pass
    
    @abstractmethod
    def get_active_by_channel(self, channel: Channel) -> Optional[NotificationSender]:
        """Get default active sender for channel."""
        pass
    
    @abstractmethod
    def list_by_channel(self, channel: Channel) -> List[NotificationSender]:
        """List all senders for channel."""
        pass
    
    @abstractmethod
    def save(self, sender: NotificationSender) -> NotificationSender:
        """Create or update sender."""
        pass


class NotificationTemplateRepository(ABC):
    """Repository for notification templates."""
    
    @abstractmethod
    def get(self, template_key: str, channel: Channel, language: str) -> Optional[NotificationTemplate]:
        """Get template by key, channel, language."""
        pass
    
    @abstractmethod
    def get_or_default_language(self, template_key: str, channel: Channel, language: str) -> Optional[NotificationTemplate]:
        """Get template; fallback to default language (en) if not found."""
        pass
    
    @abstractmethod
    def list_by_key(self, template_key: str) -> List[NotificationTemplate]:
        """List all language variants of a template."""
        pass
    
    @abstractmethod
    def list_by_channel(self, channel: Channel) -> List[NotificationTemplate]:
        """List all templates for channel."""
        pass
    
    @abstractmethod
    def save(self, template: NotificationTemplate) -> NotificationTemplate:
        """Create or update template."""
        pass
    
    @abstractmethod
    def delete(self, template_id: UUID) -> bool:
        """Delete template."""
        pass


class NotificationLogRepository(ABC):
    """Repository for notification logs."""
    
    @abstractmethod
    def save(self, log: NotificationLog) -> NotificationLog:
        """Save send log."""
        pass
    
    @abstractmethod
    def get_by_id(self, log_id: UUID) -> Optional[NotificationLog]:
        """Get log by ID."""
        pass
    
    @abstractmethod
    def list_by_template_key(self, template_key: str, limit: int = 100) -> List[NotificationLog]:
        """List recent send attempts for template."""
        pass
