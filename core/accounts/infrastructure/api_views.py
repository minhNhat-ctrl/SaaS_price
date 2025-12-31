"""
Accounts API Views - JSON endpoints for profile management

Responsibilities:
- Handle HTTP requests/responses for user profiles
- Validate input data
- Call service layer
- Return JSON responses
"""
import json
from typing import Any, Dict
from uuid import UUID

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from asgiref.sync import async_to_sync

from core.accounts.services import AccountsService
from core.accounts.domain import ProfileScope, ProfileNotFoundError
from core.accounts.infrastructure.django_repository import (
    DjangoProfileRepository,
    DjangoPreferencesRepository,
    DjangoNotificationSettingsRepository,
    DjangoAvatarRepository,
)


def _get_accounts_service() -> AccountsService:
    """Factory function to create AccountsService instance."""
    profile_repo = DjangoProfileRepository()
    preferences_repo = DjangoPreferencesRepository()
    notification_repo = DjangoNotificationSettingsRepository()
    avatar_repo = DjangoAvatarRepository()
    
    return AccountsService(
        profile_repo=profile_repo,
        preferences_repo=preferences_repo,
        notification_repo=notification_repo,
        avatar_repo=avatar_repo,
    )


def _parse_json_body(request) -> Dict[str, Any]:
    """Parse JSON body from request."""
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return {}


def _preferences_to_dict(preferences) -> Dict[str, Any]:
    """Convert UserPreferences dataclass to dictionary."""
    if not preferences:
        return {}
    
    return {
        'id': str(preferences.id),
        'user_id': str(preferences.user_id),
        'language': preferences.language,
        'timezone': preferences.timezone,
        'date_format': preferences.date_format,
        'time_format': preferences.time_format,
        'theme': preferences.theme,
        'sidebar_collapsed': preferences.sidebar_collapsed,
        'compact_mode': preferences.compact_mode,
        'items_per_page': preferences.items_per_page,
        'default_view': preferences.default_view,
        'show_onboarding': preferences.show_onboarding,
        'enable_animations': preferences.enable_animations,
        'enable_sound': preferences.enable_sound,
        'custom_preferences': preferences.custom_preferences,
        'updated_at': preferences.updated_at.isoformat() if preferences.updated_at else None,
    }


@require_http_methods(["GET"])
def get_profile_view(request):
    """
    Get current user's profile.
    
    GET /api/accounts/profile/
    
    Returns:
        200: {
            "success": true,
            "profile": {
                "id": "uuid",
                "user_id": "uuid",
                "display_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
                "email": "user@example.com",
                "bio": "...",
                "avatar_url": "...",
                "scope": "GLOBAL",
                "tenant_id": null
            }
        }
        401: {
            "success": false,
            "error": "Authentication required"
        }
        404: {
            "success": false,
            "error": "Profile not found"
        }
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    try:
        service = _get_accounts_service()
        
        # Get tenant_id from request if available (from TenantMiddleware)
        tenant_id = getattr(request, 'tenant_id', None)
        
        profile = async_to_sync(service.get_profile)(
            user_id=request.user.id,
            tenant_id=tenant_id
        )
        
        if not profile:
            return JsonResponse({
                'success': False,
                'error': 'Profile not found'
            }, status=404)
        
        return JsonResponse({
            'success': True,
            'profile': {
                'id': str(profile.id),
                'user_id': str(profile.user_id),
                'display_name': profile.display_name,
                'first_name': profile.first_name,
                'last_name': profile.last_name,
                'email': request.user.email,
                'bio': getattr(profile, 'bio', ''),
                'avatar_url': getattr(profile, 'avatar_url', ''),
                'scope': profile.scope.value,
                'tenant_id': str(profile.tenant_id) if profile.tenant_id else None,
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST", "PUT"])
def update_profile_view(request):
    """
    Create or update current user's profile.
    
    POST/PUT /api/accounts/profile/
    Body: {
        "display_name": "John Doe",
        "first_name": "John",
        "last_name": "Doe",
        "bio": "Software developer",
        "phone": "+1234567890",
        "timezone": "UTC",
        "locale": "en-US"
    }
    
    Returns:
        200: {
            "success": true,
            "profile": {...},
            "message": "Profile updated successfully"
        }
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    data = _parse_json_body(request)
    
    try:
        service = _get_accounts_service()
        tenant_id = getattr(request, 'tenant_id', None)
        
        # Try to get existing profile
        existing_profile = async_to_sync(service.get_profile)(
            user_id=request.user.id,
            tenant_id=tenant_id
        )
        
        if existing_profile:
            # Update existing profile using the proper service method
            profile = async_to_sync(service.update_profile_basic_info)(
                user_id=request.user.id,
                tenant_id=tenant_id,
                display_name=data.get('display_name'),
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                bio=data.get('bio'),
                title=data.get('title'),
                company=data.get('company'),
                location=data.get('location'),
            )
            
            # Update contact info if provided
            if any(k in data for k in ['phone', 'website', 'twitter', 'linkedin', 'github']):
                profile = async_to_sync(service.update_profile_contact)(
                    user_id=request.user.id,
                    tenant_id=tenant_id,
                    phone=data.get('phone'),
                    website=data.get('website'),
                    twitter=data.get('twitter'),
                    linkedin=data.get('linkedin'),
                    github=data.get('github'),
                )
            
            message = 'Profile updated successfully'
        else:
            # Create new profile
            scope = ProfileScope.TENANT if tenant_id else ProfileScope.GLOBAL
            profile = async_to_sync(service.create_profile)(
                user_id=request.user.id,
                scope=scope,
                tenant_id=tenant_id,
                display_name=data.get('display_name', ''),
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                bio=data.get('bio', ''),
                title=data.get('title', ''),
                company=data.get('company', ''),
                location=data.get('location', ''),
            )
            message = 'Profile created successfully'
        
        return JsonResponse({
            'success': True,
            'profile': {
                'id': str(profile.id),
                'user_id': str(profile.user_id),
                'display_name': profile.display_name,
                'first_name': profile.first_name,
                'last_name': profile.last_name,
                'bio': getattr(profile, 'bio', ''),
                'phone': getattr(profile, 'phone', ''),
                'timezone': getattr(profile, 'timezone', 'UTC'),
                'locale': getattr(profile, 'locale', 'en-US'),
                'scope': profile.scope.value,
                'tenant_id': str(profile.tenant_id) if profile.tenant_id else None,
            },
            'message': message
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_preferences_view(request):
    """
    Get current user's preferences.
    
    GET /api/accounts/preferences/
    
    Returns:
        200: {
            "success": true,
            "preferences": {
                "theme": "dark",
                "language": "en",
                "timezone": "UTC",
                "date_format": "YYYY-MM-DD",
                "time_format": "24h",
                ...
            }
        }
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    try:
        service = _get_accounts_service()
        tenant_id = getattr(request, 'tenant_id', None)
        
        preferences = async_to_sync(service.get_preferences)(
            user_id=request.user.id,
            tenant_id=tenant_id
        )
        
        if not preferences:
            return JsonResponse({
                'success': True,
                'preferences': {}
            }, status=200)
        
        return JsonResponse({
            'success': True,
            'preferences': _preferences_to_dict(preferences)
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST", "PUT"])
def update_preferences_view(request):
    """
    Update current user's preferences.
    
    POST/PUT /api/accounts/preferences/
    Body: {
        "theme": "dark",
        "language": "en",
        "timezone": "UTC",
        ...
    }
    
    Returns:
        200: {
            "success": true,
            "preferences": {...},
            "message": "Preferences updated successfully"
        }
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    data = _parse_json_body(request)
    
    try:
        service = _get_accounts_service()
        tenant_id = getattr(request, 'tenant_id', None)
        
        preferences = async_to_sync(service.update_preferences)(
            user_id=request.user.id,
            tenant_id=tenant_id,
            **data
        )
        
        return JsonResponse({
            'success': True,
            'preferences': _preferences_to_dict(preferences),
            'message': 'Preferences updated successfully'
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
