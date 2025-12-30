"""
Repository Interfaces for Accounts Module

Abstract interfaces for data access - no implementation details.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from core.accounts.domain import (
    UserProfile,
    ProfileScope,
    UserPreferences,
    NotificationSettings,
    Avatar,
)


class ProfileRepository(ABC):
    """Repository interface for UserProfile operations."""
    
    @abstractmethod
    async def create(self, profile: UserProfile) -> UserProfile:
        """Create new user profile."""
        pass
    
    @abstractmethod
    async def get_by_id(self, profile_id: UUID) -> Optional[UserProfile]:
        """Get profile by ID."""
        pass
    
    @abstractmethod
    async def get_by_user(
        self, 
        user_id: UUID, 
        tenant_id: Optional[UUID] = None
    ) -> Optional[UserProfile]:
        """Get profile by user ID (optionally scoped to tenant)."""
        pass
    
    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID) -> List[UserProfile]:
        """List all profiles in a tenant."""
        pass
    
    @abstractmethod
    async def update(self, profile: UserProfile) -> UserProfile:
        """Update profile."""
        pass
    
    @abstractmethod
    async def delete(self, profile_id: UUID) -> bool:
        """Delete profile."""
        pass
    
    @abstractmethod
    async def search(
        self, 
        query: str, 
        tenant_id: Optional[UUID] = None
    ) -> List[UserProfile]:
        """Search profiles by name/email."""
        pass


class PreferencesRepository(ABC):
    """Repository interface for UserPreferences operations."""
    
    @abstractmethod
    async def create(self, preferences: UserPreferences) -> UserPreferences:
        """Create user preferences."""
        pass
    
    @abstractmethod
    async def get_by_user(
        self, 
        user_id: UUID, 
        tenant_id: Optional[UUID] = None
    ) -> Optional[UserPreferences]:
        """Get preferences by user ID."""
        pass
    
    @abstractmethod
    async def update(self, preferences: UserPreferences) -> UserPreferences:
        """Update preferences."""
        pass
    
    @abstractmethod
    async def delete(self, user_id: UUID, tenant_id: Optional[UUID] = None) -> bool:
        """Delete preferences."""
        pass


class NotificationSettingsRepository(ABC):
    """Repository interface for NotificationSettings operations."""
    
    @abstractmethod
    async def create(self, settings: NotificationSettings) -> NotificationSettings:
        """Create notification settings."""
        pass
    
    @abstractmethod
    async def get_by_user(
        self, 
        user_id: UUID, 
        tenant_id: Optional[UUID] = None
    ) -> Optional[NotificationSettings]:
        """Get notification settings by user ID."""
        pass
    
    @abstractmethod
    async def update(self, settings: NotificationSettings) -> NotificationSettings:
        """Update notification settings."""
        pass
    
    @abstractmethod
    async def delete(self, user_id: UUID, tenant_id: Optional[UUID] = None) -> bool:
        """Delete notification settings."""
        pass


class AvatarRepository(ABC):
    """Repository interface for Avatar operations."""
    
    @abstractmethod
    async def create(self, avatar: Avatar) -> Avatar:
        """Create/upload avatar."""
        pass
    
    @abstractmethod
    async def get_by_user(
        self, 
        user_id: UUID, 
        tenant_id: Optional[UUID] = None
    ) -> Optional[Avatar]:
        """Get avatar by user ID."""
        pass
    
    @abstractmethod
    async def update(self, avatar: Avatar) -> Avatar:
        """Update avatar metadata."""
        pass
    
    @abstractmethod
    async def delete(self, avatar_id: UUID) -> bool:
        """Delete avatar (including file)."""
        pass
    
    @abstractmethod
    async def upload_file(self, avatar_id: UUID, file_data: bytes, filename: str) -> str:
        """
        Upload avatar file to storage.
        
        Returns: File path in storage
        """
        pass
