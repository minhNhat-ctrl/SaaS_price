"""
Accounts Service - User Profile & Preferences Management

Business logic for managing user profiles, preferences, and notifications.
No Django dependencies - pure business logic.
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from core.accounts.domain import (
    UserProfile,
    ProfileScope,
    UserPreferences,
    NotificationSettings,
    NotificationChannel,
    Avatar,
    ProfileNotFoundError,
    ProfileAlreadyExistsError,
    InvalidAvatarError,
    InvalidPreferenceError,
)
from core.accounts.repositories import (
    ProfileRepository,
    PreferencesRepository,
    NotificationSettingsRepository,
    AvatarRepository,
)


class AccountsService:
    """
    Main service for accounts operations.
    
    Responsibilities:
    - Profile management (create, update, delete)
    - Preferences management
    - Notification settings
    - Avatar upload and management
    """
    
    def __init__(
        self,
        profile_repo: ProfileRepository,
        preferences_repo: PreferencesRepository,
        notification_repo: NotificationSettingsRepository,
        avatar_repo: AvatarRepository,
    ):
        self.profile_repo = profile_repo
        self.preferences_repo = preferences_repo
        self.notification_repo = notification_repo
        self.avatar_repo = avatar_repo
    
    # ============================================================
    # Profile Management
    # ============================================================
    
    async def create_profile(
        self,
        user_id: UUID,
        scope: ProfileScope = ProfileScope.GLOBAL,
        tenant_id: Optional[UUID] = None,
        display_name: str = "",
        first_name: str = "",
        last_name: str = "",
        **kwargs
    ) -> UserProfile:
        """
        Create new user profile.
        
        Args:
            user_id: User ID from identity module
            scope: Global or tenant-specific
            tenant_id: Required if scope=TENANT
            display_name: Display name
            first_name: First name
            last_name: Last name
            **kwargs: Additional profile fields
        
        Returns:
            Created profile
        
        Raises:
            ProfileAlreadyExistsError: If profile exists
        """
        # Check if profile already exists
        existing = await self.profile_repo.get_by_user(user_id, tenant_id)
        if existing:
            raise ProfileAlreadyExistsError(str(user_id), str(tenant_id) if tenant_id else None)
        
        # Create profile
        profile = UserProfile(
            id=UUID(int=0),  # Will be set by repository
            user_id=user_id,
            scope=scope,
            tenant_id=tenant_id,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            **kwargs
        )
        
        # Create default preferences
        preferences = UserPreferences(
            id=UUID(int=0),
            user_id=user_id,
            tenant_id=tenant_id,
        )
        profile.preferences = await self.preferences_repo.create(preferences)
        
        # Create default notification settings
        notification_settings = NotificationSettings(
            id=UUID(int=0),
            user_id=user_id,
            tenant_id=tenant_id,
        )
        profile.notification_settings = await self.notification_repo.create(notification_settings)
        
        return await self.profile_repo.create(profile)
    
    async def get_profile(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None
    ) -> Optional[UserProfile]:
        """Get user profile."""
        return await self.profile_repo.get_by_user(user_id, tenant_id)
    
    async def get_or_create_profile(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
        **kwargs
    ) -> UserProfile:
        """Get profile or create if not exists."""
        profile = await self.get_profile(user_id, tenant_id)
        if not profile:
            scope = ProfileScope.TENANT if tenant_id else ProfileScope.GLOBAL
            profile = await self.create_profile(
                user_id=user_id,
                scope=scope,
                tenant_id=tenant_id,
                **kwargs
            )
        return profile
    
    async def update_profile_basic_info(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
        display_name: str = None,
        first_name: str = None,
        last_name: str = None,
        bio: str = None,
        title: str = None,
        company: str = None,
        location: str = None,
    ) -> UserProfile:
        """
        Update basic profile information.
        
        Raises:
            ProfileNotFoundError: If profile doesn't exist
        """
        profile = await self.profile_repo.get_by_user(user_id, tenant_id)
        if not profile:
            raise ProfileNotFoundError(str(user_id), str(tenant_id) if tenant_id else None)
        
        profile.update_basic_info(
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            bio=bio,
            title=title,
            company=company,
            location=location,
        )
        
        return await self.profile_repo.update(profile)
    
    async def update_profile_contact(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
        phone: str = None,
        website: str = None,
        twitter: str = None,
        linkedin: str = None,
        github: str = None,
    ) -> UserProfile:
        """Update contact information."""
        profile = await self.profile_repo.get_by_user(user_id, tenant_id)
        if not profile:
            raise ProfileNotFoundError(str(user_id), str(tenant_id) if tenant_id else None)
        
        profile.update_contact_info(
            phone=phone,
            website=website,
            twitter=twitter,
            linkedin=linkedin,
            github=github,
        )
        
        return await self.profile_repo.update(profile)
    
    async def delete_profile(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None
    ) -> bool:
        """Delete user profile."""
        profile = await self.profile_repo.get_by_user(user_id, tenant_id)
        if profile:
            return await self.profile_repo.delete(profile.id)
        return False
    
    async def search_profiles(
        self,
        query: str,
        tenant_id: Optional[UUID] = None
    ) -> List[UserProfile]:
        """Search profiles by name/email."""
        return await self.profile_repo.search(query, tenant_id)
    
    # ============================================================
    # Preferences Management
    # ============================================================
    
    async def get_preferences(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None
    ) -> Optional[UserPreferences]:
        """Get user preferences."""
        return await self.preferences_repo.get_by_user(user_id, tenant_id)
    
    async def update_preferences(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
        **preferences_data
    ) -> UserPreferences:
        """
        Update user preferences.
        
        Args:
            user_id: User ID
            tenant_id: Optional tenant ID
            **preferences_data: Preference fields to update
        
        Returns:
            Updated preferences
        """
        prefs = await self.preferences_repo.get_by_user(user_id, tenant_id)
        
        if not prefs:
            # Create if not exists
            prefs = UserPreferences(
                id=UUID(int=0),
                user_id=user_id,
                tenant_id=tenant_id,
            )
        
        # Update fields
        for key, value in preferences_data.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)
        
        prefs.updated_at = datetime.utcnow()
        
        if prefs.id.int == 0:
            return await self.preferences_repo.create(prefs)
        else:
            return await self.preferences_repo.update(prefs)
    
    async def set_custom_preference(
        self,
        user_id: UUID,
        key: str,
        value: Any,
        tenant_id: Optional[UUID] = None
    ) -> UserPreferences:
        """Set custom preference value."""
        prefs = await self.get_preferences(user_id, tenant_id)
        if not prefs:
            prefs = UserPreferences(
                id=UUID(int=0),
                user_id=user_id,
                tenant_id=tenant_id,
            )
            prefs = await self.preferences_repo.create(prefs)
        
        prefs.set_preference(key, value)
        return await self.preferences_repo.update(prefs)
    
    async def get_custom_preference(
        self,
        user_id: UUID,
        key: str,
        default: Any = None,
        tenant_id: Optional[UUID] = None
    ) -> Any:
        """Get custom preference value."""
        prefs = await self.get_preferences(user_id, tenant_id)
        if prefs:
            return prefs.get_preference(key, default)
        return default
    
    # ============================================================
    # Notification Settings
    # ============================================================
    
    async def get_notification_settings(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None
    ) -> Optional[NotificationSettings]:
        """Get notification settings."""
        return await self.notification_repo.get_by_user(user_id, tenant_id)
    
    async def update_notification_settings(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
        **settings_data
    ) -> NotificationSettings:
        """Update notification settings."""
        settings = await self.notification_repo.get_by_user(user_id, tenant_id)
        
        if not settings:
            settings = NotificationSettings(
                id=UUID(int=0),
                user_id=user_id,
                tenant_id=tenant_id,
            )
        
        # Update fields
        for key, value in settings_data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        settings.updated_at = datetime.utcnow()
        
        if settings.id.int == 0:
            return await self.notification_repo.create(settings)
        else:
            return await self.notification_repo.update(settings)
    
    async def enable_notification_channel(
        self,
        user_id: UUID,
        channel: NotificationChannel,
        tenant_id: Optional[UUID] = None
    ) -> NotificationSettings:
        """Enable notification channel."""
        settings = await self.get_notification_settings(user_id, tenant_id)
        if not settings:
            settings = NotificationSettings(
                id=UUID(int=0),
                user_id=user_id,
                tenant_id=tenant_id,
            )
            settings = await self.notification_repo.create(settings)
        
        settings.enable_channel(channel)
        return await self.notification_repo.update(settings)
    
    async def disable_notification_channel(
        self,
        user_id: UUID,
        channel: NotificationChannel,
        tenant_id: Optional[UUID] = None
    ) -> NotificationSettings:
        """Disable notification channel."""
        settings = await self.get_notification_settings(user_id, tenant_id)
        if settings:
            settings.disable_channel(channel)
            return await self.notification_repo.update(settings)
        return settings
    
    # ============================================================
    # Avatar Management
    # ============================================================
    
    async def upload_avatar(
        self,
        user_id: UUID,
        file_data: bytes,
        filename: str,
        mime_type: str = "image/jpeg",
        tenant_id: Optional[UUID] = None
    ) -> Avatar:
        """
        Upload user avatar.
        
        Args:
            user_id: User ID
            file_data: Avatar file bytes
            filename: Original filename
            mime_type: MIME type
            tenant_id: Optional tenant ID
        
        Returns:
            Created avatar
        
        Raises:
            InvalidAvatarError: If file is invalid
        """
        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024
        if len(file_data) > max_size:
            raise InvalidAvatarError(f"File too large: {len(file_data)} bytes (max {max_size})")
        
        # Validate MIME type
        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if mime_type not in allowed_types:
            raise InvalidAvatarError(f"Invalid MIME type: {mime_type}")
        
        # Create avatar entity
        avatar = Avatar(
            id=UUID(int=0),
            user_id=user_id,
            tenant_id=tenant_id,
            file_size=len(file_data),
            mime_type=mime_type,
        )
        
        # Save to database first
        avatar = await self.avatar_repo.create(avatar)
        
        # Upload file to storage
        file_path = await self.avatar_repo.upload_file(avatar.id, file_data, filename)
        avatar.file_path = file_path
        
        # Update with file path
        avatar = await self.avatar_repo.update(avatar)
        
        # Update profile with avatar
        profile = await self.profile_repo.get_by_user(user_id, tenant_id)
        if profile:
            profile.set_avatar(avatar)
            await self.profile_repo.update(profile)
        
        return avatar
    
    async def set_external_avatar(
        self,
        user_id: UUID,
        external_url: str,
        tenant_id: Optional[UUID] = None
    ) -> Avatar:
        """Set external avatar URL (e.g., Gravatar)."""
        avatar = Avatar(
            id=UUID(int=0),
            user_id=user_id,
            tenant_id=tenant_id,
            external_url=external_url,
        )
        
        avatar = await self.avatar_repo.create(avatar)
        
        # Update profile with avatar
        profile = await self.profile_repo.get_by_user(user_id, tenant_id)
        if profile:
            profile.set_avatar(avatar)
            await self.profile_repo.update(profile)
        
        return avatar
    
    async def delete_avatar(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None
    ) -> bool:
        """Delete user avatar."""
        avatar = await self.avatar_repo.get_by_user(user_id, tenant_id)
        if avatar:
            # Update profile to remove avatar
            profile = await self.profile_repo.get_by_user(user_id, tenant_id)
            if profile:
                profile.avatar = None
                await self.profile_repo.update(profile)
            
            return await self.avatar_repo.delete(avatar.id)
        return False
