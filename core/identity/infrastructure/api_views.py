"""
"""Backwards compatibility shims for legacy imports.

The HTTP layer now lives under core.identity.api.views. Keep these re-exports
until all includes are migrated to the new paths.
"""

from core.identity.api.views import *  # noqa: F401,F403
            "message": "Login successful",
            "user": {...}
        }
    """
    data = _parse_json_body(request)
    token = data.get('token', '').strip()
    
    if not token:
        return JsonResponse({
            'success': False,
            'error': 'Token is required'
        }, status=400)
    
    try:
        service = _get_identity_service()
        auth_token = async_to_sync(service.authenticate_with_magic_link)(token)
        
        # Create Django session
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=auth_token.user_id)
        
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
        return JsonResponse({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': str(user.id),
                'email': user.email
            }
        }, status=200)
        
    except InvalidCredentialError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except IdentityNotFoundError:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
