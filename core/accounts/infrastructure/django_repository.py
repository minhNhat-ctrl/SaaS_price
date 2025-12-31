"""
Django Repository Implementations for Accounts Module

Implements repository interfaces using Django ORM.
"""
from typing import List, Optional
from uuid import UUID

from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist

from core.accounts.domain import (
    UserProfile as DomainProfile,
    ProfileScope,
    UserPreferences as DomainPreferences,
    NotificationSettings as DomainNotificationSettings,
    Avatar as DomainAvatar,
)
from core.accounts.repositories import (
    ProfileRepository,
    PreferencesRepository,
    NotificationSettingsRepository,
    AvatarRepository,
)
from core.accounts.infrastructure import django_models as models


def _profile_model_to_domain(model: models.UserProfile) -> DomainProfile:
    """Convert Django model to domain entity."""
    return DomainProfile(
        id=model.id,
        user_id=model.user_id,
        scope=ProfileScope(model.scope.lower()),
        tenant_id=model.tenant_id,
        display_name=model.display_name,
        first_name=model.first_name,
        last_name=model.last_name,
        bio=model.bio,
        title=model.title,
        company=model.company,
        location=model.location,
        phone=model.phone,
        website=model.website,
        twitter=model.twitter,
        linkedin=model.linkedin,
        github=model.github,
        is_public=model.is_public,
        is_verified=model.is_verified,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _profile_domain_to_model(domain: DomainProfile, model: Optional[models.UserProfile] = None) -> models.UserProfile:
    """Convert domain entity to Django model."""
    if model is None:
        model = models.UserProfile()
    
    model.id = domain.id
    model.user_id = domain.user_id
    model.scope = domain.scope.value.upper()
    model.tenant_id = domain.tenant_id
    model.display_name = domain.display_name
    model.first_name = domain.first_name
    model.last_name = domain.last_name
    model.bio = getattr(domain, 'bio', '')
    model.title = getattr(domain, 'title', '')
    model.company = getattr(domain, 'company', '')
    model.location = getattr(domain, 'location', '')
    model.phone = getattr(domain, 'phone', '')
    model.website = getattr(domain, 'website', '')
    model.twitter = getattr(domain, 'twitter', '')
    model.linkedin = getattr(domain, 'linkedin', '')
    model.github = getattr(domain, 'github', '')
    
    return model


class DjangoProfileRepository(ProfileRepository):
    """Django ORM implementation of ProfileRepository."""
    
    async def create(self, profile: DomainProfile) -> DomainProfile:
        @sync_to_async
        def _create():
            model = _profile_domain_to_model(profile)
            model.save()
            return _profile_model_to_domain(model)
        
        return await _create()
    
    async def get_by_id(self, profile_id: UUID) -> Optional[DomainProfile]:
        @sync_to_async
        def _get():
            try:
                model = models.UserProfile.objects.get(id=profile_id)
                return _profile_model_to_domain(model)
            except ObjectDoesNotExist:
                return None
        
        return await _get()
    
    async def get_by_user(
        self, 
        user_id: UUID, 
        tenant_id: Optional[UUID] = None
    ) -> Optional[DomainProfile]:
        @sync_to_async
        def _get():
            try:
                query = {'user_id': user_id}
                if tenant_id:
                    query['tenant_id'] = tenant_id
                else:
                    query['tenant_id__isnull'] = True
                
                model = models.UserProfile.objects.get(**query)
                return _profile_model_to_domain(model)
            except ObjectDoesNotExist:
                return None
        
        return await _get()
    
    async def list_by_tenant(self, tenant_id: UUID) -> List[DomainProfile]:
        @sync_to_async
        def _list():
            queryset = models.UserProfile.objects.filter(tenant_id=tenant_id)
            return [_profile_model_to_domain(m) for m in queryset]
        
        return await _list()
    
    async def update(self, profile: DomainProfile) -> DomainProfile:
        @sync_to_async
        def _update():
            model = models.UserProfile.objects.get(id=profile.id)
            model = _profile_domain_to_model(profile, model)
            model.save()
            return _profile_model_to_domain(model)
        
        return await _update()
    
    async def delete(self, profile_id: UUID) -> bool:
        @sync_to_async
        def _delete():
            try:
                models.UserProfile.objects.filter(id=profile_id).delete()
                return True
            except Exception:
                return False
        
        return await _delete()
    
    async def search(
        self, 
        query: str, 
        tenant_id: Optional[UUID] = None
    ) -> List[DomainProfile]:
        @sync_to_async
        def _search():
            qs = models.UserProfile.objects.filter(
                display_name__icontains=query
            ) | models.UserProfile.objects.filter(
                first_name__icontains=query
            ) | models.UserProfile.objects.filter(
                last_name__icontains=query
            )
            
            if tenant_id:
                qs = qs.filter(tenant_id=tenant_id)
            
            return [_profile_model_to_domain(m) for m in qs]
        
        return await _search()


def _preferences_model_to_domain(model: models.UserPreferences) -> DomainPreferences:
    """Convert Django model to domain entity."""
    return DomainPreferences(
        id=model.id,
        user_id=model.user_id,
        tenant_id=model.tenant_id,
        theme=model.theme,
        language=model.language,
        timezone=model.timezone,
        date_format=model.date_format,
        time_format=model.time_format,
        items_per_page=model.items_per_page,
        sidebar_collapsed=model.sidebar_collapsed,
        preferences=model.custom_preferences,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class DjangoPreferencesRepository(PreferencesRepository):
    """Django ORM implementation of PreferencesRepository."""
    
    async def create(self, preferences: DomainPreferences) -> DomainPreferences:
        @sync_to_async
        def _create():
            model = models.UserPreferences(
                user_id=preferences.user_id,
                tenant_id=preferences.tenant_id,
                theme=getattr(preferences, 'theme', 'LIGHT'),
                language=getattr(preferences, 'language', 'en'),
                timezone=getattr(preferences, 'timezone', 'UTC'),
                custom_preferences=getattr(preferences, 'preferences', {}),
            )
            model.save()
            return _preferences_model_to_domain(model)
        
        return await _create()
    
    async def get_by_user(
        self, 
        user_id: UUID, 
        tenant_id: Optional[UUID] = None
    ) -> Optional[DomainPreferences]:
        @sync_to_async
        def _get():
            try:
                query = {'user_id': user_id}
                if tenant_id:
                    query['tenant_id'] = tenant_id
                else:
                    query['tenant_id__isnull'] = True
                
                model = models.UserPreferences.objects.get(**query)
                return _preferences_model_to_domain(model)
            except ObjectDoesNotExist:
                return None
        
        return await _get()
    
    async def update(self, preferences: DomainPreferences) -> DomainPreferences:
        @sync_to_async
        def _update():
            model = models.UserPreferences.objects.get(id=preferences.id)
            model.theme = getattr(preferences, 'theme', model.theme)
            model.language = getattr(preferences, 'language', model.language)
            model.timezone = getattr(preferences, 'timezone', model.timezone)
            model.custom_preferences = getattr(preferences, 'preferences', model.custom_preferences)
            model.save()
            return _preferences_model_to_domain(model)
        
        return await _update()
    
    async def delete(self, user_id: UUID, tenant_id: Optional[UUID] = None) -> bool:
        @sync_to_async
        def _delete():
            try:
                query = {'user_id': user_id}
                if tenant_id:
                    query['tenant_id'] = tenant_id
                else:
                    query['tenant_id__isnull'] = True
                
                models.UserPreferences.objects.filter(**query).delete()
                return True
            except Exception:
                return False
        
        return await _delete()


class DjangoNotificationSettingsRepository(NotificationSettingsRepository):
    """Django ORM implementation of NotificationSettingsRepository."""
    
    async def create(self, settings: DomainNotificationSettings) -> DomainNotificationSettings:
        @sync_to_async
        def _create():
            model = models.NotificationSettings(
                user_id=settings.user_id,
                tenant_id=settings.tenant_id,
            )
            model.save()
            return settings
        
        return await _create()
    
    async def get_by_user(
        self, 
        user_id: UUID, 
        tenant_id: Optional[UUID] = None
    ) -> Optional[DomainNotificationSettings]:
        @sync_to_async
        def _get():
            try:
                query = {'user_id': user_id}
                if tenant_id:
                    query['tenant_id'] = tenant_id
                else:
                    query['tenant_id__isnull'] = True
                
                model = models.NotificationSettings.objects.get(**query)
                return DomainNotificationSettings(
                    id=model.id,
                    user_id=model.user_id,
                    tenant_id=model.tenant_id,
                    email_enabled=model.email_enabled,
                    sms_enabled=model.sms_enabled,
                    push_enabled=model.push_enabled,
                    in_app_enabled=model.in_app_enabled,
                )
            except ObjectDoesNotExist:
                return None
        
        return await _get()
    
    async def update(self, settings: DomainNotificationSettings) -> DomainNotificationSettings:
        @sync_to_async
        def _update():
            model = models.NotificationSettings.objects.get(id=settings.id)
            model.email_enabled = settings.email_enabled
            model.sms_enabled = settings.sms_enabled
            model.push_enabled = settings.push_enabled
            model.in_app_enabled = settings.in_app_enabled
            model.save()
            return settings
        
        return await _update()
    
    async def delete(self, user_id: UUID, tenant_id: Optional[UUID] = None) -> bool:
        @sync_to_async
        def _delete():
            try:
                query = {'user_id': user_id}
                if tenant_id:
                    query['tenant_id'] = tenant_id
                else:
                    query['tenant_id__isnull'] = True
                
                models.NotificationSettings.objects.filter(**query).delete()
                return True
            except Exception:
                return False
        
        return await _delete()


class DjangoAvatarRepository(AvatarRepository):
    """Django ORM implementation of AvatarRepository."""
    
    async def create(self, avatar: DomainAvatar) -> DomainAvatar:
        @sync_to_async
        def _create():
            model = models.Avatar(
                user_id=avatar.user_id,
                tenant_id=avatar.tenant_id,
                external_url=getattr(avatar, 'external_url', ''),
            )
            model.save()
            return avatar
        
        return await _create()
    
    async def get_by_user(
        self, 
        user_id: UUID, 
        tenant_id: Optional[UUID] = None
    ) -> Optional[DomainAvatar]:
        @sync_to_async
        def _get():
            try:
                query = {'user_id': user_id, 'is_active': True}
                if tenant_id:
                    query['tenant_id'] = tenant_id
                
                model = models.Avatar.objects.filter(**query).first()
                if not model:
                    return None
                
                return DomainAvatar(
                    id=model.id,
                    user_id=model.user_id,
                    tenant_id=model.tenant_id,
                    external_url=model.external_url,
                    file_url=model.url,
                )
            except Exception:
                return None
        
        return await _get()
    
    async def update(self, avatar: DomainAvatar) -> DomainAvatar:
        @sync_to_async
        def _update():
            model = models.Avatar.objects.get(id=avatar.id)
            model.external_url = getattr(avatar, 'external_url', model.external_url)
            model.save()
            return avatar
        
        return await _update()
    
    async def delete(self, avatar_id: UUID) -> bool:
        @sync_to_async
        def _delete():
            try:
                models.Avatar.objects.filter(id=avatar_id).delete()
                return True
            except Exception:
                return False
        
        return await _delete()
