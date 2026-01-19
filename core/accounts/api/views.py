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

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from asgiref.sync import async_to_sync

from core.accounts.services.providers import get_accounts_service
from core.accounts.domain import ProfileScope, ProfileNotFoundError, InvalidAvatarError


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


def _notification_settings_to_dict(settings) -> Dict[str, Any]:
    """Convert NotificationSettings dataclass to dictionary."""
    if not settings:
        return {}

    return {
        'id': str(settings.id),
        'user_id': str(settings.user_id),
        'tenant_id': str(settings.tenant_id) if settings.tenant_id else None,
        'email_enabled': settings.email_enabled,
        'sms_enabled': settings.sms_enabled,
        'push_enabled': settings.push_enabled,
        'in_app_enabled': settings.in_app_enabled,
        'marketing_enabled': settings.marketing_enabled,
        'product_updates_enabled': settings.product_updates_enabled,
        'security_alerts_enabled': settings.security_alerts_enabled,
        'mentions_enabled': settings.mentions_enabled,
        'daily_digest': settings.daily_digest,
        'weekly_digest': settings.weekly_digest,
        'quiet_hours_start': settings.quiet_hours_start,
        'quiet_hours_end': settings.quiet_hours_end,
        'custom_settings': settings.custom_settings,
        'updated_at': settings.updated_at.isoformat() if settings.updated_at else None,
    }


def _avatar_to_dict(avatar) -> Dict[str, Any]:
    """Convert Avatar dataclass to dictionary."""
    if not avatar:
        return {}

    return {
        'id': str(avatar.id),
        'user_id': str(avatar.user_id),
        'tenant_id': str(avatar.tenant_id) if avatar.tenant_id else None,
        'file_path': avatar.file_path,
        'file_url': avatar.get_url() if hasattr(avatar, 'get_url') else avatar.file_url,
        'external_url': avatar.external_url,
        'file_size': avatar.file_size,
        'mime_type': avatar.mime_type,
        'width': avatar.width,
        'height': avatar.height,
        'uploaded_at': avatar.uploaded_at.isoformat() if getattr(avatar, 'uploaded_at', None) else None,
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
        service = get_accounts_service()
        
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
                'title': getattr(profile, 'title', ''),
                'company': getattr(profile, 'company', ''),
                'location': getattr(profile, 'location', ''),
                'phone': getattr(profile, 'phone', ''),
                'website': getattr(profile, 'website', ''),
                'twitter': getattr(profile, 'twitter', ''),
                'linkedin': getattr(profile, 'linkedin', ''),
                'github': getattr(profile, 'github', ''),
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
        service = get_accounts_service()
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
                'title': getattr(profile, 'title', ''),
                'company': getattr(profile, 'company', ''),
                'location': getattr(profile, 'location', ''),
                'phone': getattr(profile, 'phone', ''),
                'website': getattr(profile, 'website', ''),
                'twitter': getattr(profile, 'twitter', ''),
                'linkedin': getattr(profile, 'linkedin', ''),
                'github': getattr(profile, 'github', ''),
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
        service = get_accounts_service()
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


@require_http_methods(["GET"])
def get_notification_settings_view(request):
    """Get current user's notification settings."""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)

    try:
        service = get_accounts_service()
        tenant_id = getattr(request, 'tenant_id', None)

        settings = async_to_sync(service.get_notification_settings)(
            user_id=request.user.id,
            tenant_id=tenant_id
        )

        return JsonResponse({
            'success': True,
            'notification_settings': _notification_settings_to_dict(settings)
        }, status=200)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST", "PUT"])
def update_notification_settings_view(request):
    """Update notification settings."""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)

    data = _parse_json_body(request)

    try:
        service = get_accounts_service()
        tenant_id = getattr(request, 'tenant_id', None)

        settings = async_to_sync(service.update_notification_settings)(
            user_id=request.user.id,
            tenant_id=tenant_id,
            **data
        )

        return JsonResponse({
            'success': True,
            'notification_settings': _notification_settings_to_dict(settings),
            'message': 'Notification settings updated successfully'
        }, status=200)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_avatar_view(request):
    """Get current user's avatar metadata."""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)

    try:
        service = get_accounts_service()
        tenant_id = getattr(request, 'tenant_id', None)

        profile = async_to_sync(service.get_profile)(
            user_id=request.user.id,
            tenant_id=tenant_id
        )

        avatar_data = _avatar_to_dict(profile.avatar) if profile and profile.avatar else {}

        return JsonResponse({
            'success': True,
            'avatar': avatar_data
        }, status=200)

    except ProfileNotFoundError:
        return JsonResponse({
            'success': False,
            'error': 'Profile not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def upload_avatar_view(request):
    """Upload a new avatar for the current user."""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)

    try:
        service = get_accounts_service()
        tenant_id = getattr(request, 'tenant_id', None)

        if request.content_type and 'application/json' in request.content_type:
            data = _parse_json_body(request)
            external_url = data.get('external_url')
            if not external_url:
                return JsonResponse({
                    'success': False,
                    'error': 'external_url is required for JSON requests'
                }, status=400)

            avatar = async_to_sync(service.set_external_avatar)(
                user_id=request.user.id,
                tenant_id=tenant_id,
                external_url=external_url
            )
        else:
            avatar_file = request.FILES.get('avatar')
            if not avatar_file:
                return JsonResponse({
                    'success': False,
                    'error': 'Avatar file is required'
                }, status=400)

            file_data = avatar_file.read()
            avatar = async_to_sync(service.upload_avatar)(
                user_id=request.user.id,
                tenant_id=tenant_id,
                file_data=file_data,
                filename=avatar_file.name,
                mime_type=getattr(avatar_file, 'content_type', 'image/jpeg')
            )

        return JsonResponse({
            'success': True,
            'avatar': _avatar_to_dict(avatar),
            'message': 'Avatar updated successfully'
        }, status=200)

    except InvalidAvatarError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def remove_avatar_view(request):
    """Remove the current user's avatar."""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)

    try:
        service = get_accounts_service()
        tenant_id = getattr(request, 'tenant_id', None)

        removed = async_to_sync(service.delete_avatar)(
            user_id=request.user.id,
            tenant_id=tenant_id
        )

        if not removed:
            return JsonResponse({
                'success': False,
                'error': 'Avatar not found'
            }, status=404)

        return JsonResponse({
            'success': True,
            'message': 'Avatar removed successfully'
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
        service = get_accounts_service()
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
