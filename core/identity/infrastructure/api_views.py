"""
Identity API Views - JSON endpoints for authentication

Responsibilities:
- Handle HTTP requests/responses
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
from django.contrib.auth import login, logout
from asgiref.sync import async_to_sync

from core.identity.services import IdentityService
from core.identity.infrastructure.django_repository import DjangoAllauthIdentityRepository
from core.identity.domain.exceptions import (
    IdentityAlreadyExistsError,
    IdentityNotFoundError,
    InvalidCredentialError,
)


def _get_identity_service() -> IdentityService:
    """Factory function to create IdentityService instance."""
    repository = DjangoAllauthIdentityRepository()
    return IdentityService(repository)


def _parse_json_body(request) -> Dict[str, Any]:
    """Parse JSON body from request."""
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return {}


@csrf_exempt
@require_http_methods(["POST"])
def signup_view(request):
    """
    User registration endpoint.
    
    POST /api/identity/signup/
    Body: {
        "email": "user@example.com",
        "password": "securepass123",
        "email_verified": false
    }
    
    Returns:
        201: {
            "success": true,
            "user_id": "uuid",
            "email": "user@example.com",
            "message": "User registered successfully"
        }
        400: {
            "success": false,
            "error": "Email already exists"
        }
    """
    data = _parse_json_body(request)
    
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    email_verified = data.get('email_verified', False)
    
    # Validation
    if not email or not password:
        return JsonResponse({
            'success': False,
            'error': 'Email and password are required'
        }, status=400)
    
    if len(password) < 8:
        return JsonResponse({
            'success': False,
            'error': 'Password must be at least 8 characters'
        }, status=400)
    
    try:
        service = _get_identity_service()
        identity = async_to_sync(service.register_user)(
            email=email,
            password=password,
            email_verified=email_verified
        )
        
        return JsonResponse({
            'success': True,
            'user_id': str(identity.id),
            'email': identity.email,
            'message': 'User registered successfully'
        }, status=201)
        
    except IdentityAlreadyExistsError:
        return JsonResponse({
            'success': False,
            'error': 'Email already exists'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    """
    User login endpoint.
    
    POST /api/identity/login/
    Body: {
        "email": "user@example.com",
        "password": "securepass123"
    }
    
    Returns:
        200: {
            "success": true,
            "user_id": "uuid",
            "email": "user@example.com",
            "token": "auth_token",
            "message": "Login successful"
        }
        401: {
            "success": false,
            "error": "Invalid credentials"
        }
    """
    data = _parse_json_body(request)
    
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    if not email or not password:
        return JsonResponse({
            'success': False,
            'error': 'Email and password are required'
        }, status=400)
    
    try:
        service = _get_identity_service()
        auth_token = async_to_sync(service.authenticate)(
            email=email,
            password=password
        )
        
        # Create Django session
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=auth_token.user_id)
        login(request, user)
        
        return JsonResponse({
            'success': True,
            'user_id': str(auth_token.user_id),
            'email': email,
            'token': auth_token.token,
            'message': 'Login successful'
        }, status=200)
        
    except InvalidCredentialError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid email or password'
        }, status=401)
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


@csrf_exempt
@require_http_methods(["POST"])
def logout_view(request):
    """
    User logout endpoint.
    
    POST /api/identity/logout/
    
    Returns:
        200: {
            "success": true,
            "message": "Logout successful"
        }
    """
    logout(request)
    
    return JsonResponse({
        'success': True,
        'message': 'Logout successful'
    }, status=200)


@require_http_methods(["GET"])
def check_auth_view(request):
    """
    Check authentication status.
    
    GET /api/identity/check-auth/
    
    Returns:
        200: {
            "authenticated": true,
            "user_id": "uuid",
            "email": "user@example.com"
        }
    """
    if request.user.is_authenticated:
        return JsonResponse({
            'authenticated': True,
            'user_id': str(request.user.id),
            'email': request.user.email
        }, status=200)
    else:
        return JsonResponse({
            'authenticated': False
        }, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def change_password_view(request):
    """
    Change user password.
    
    POST /api/identity/change-password/
    Body: {
        "email": "user@example.com",
        "new_password": "newsecurepass123"
    }
    
    Returns:
        200: {
            "success": true,
            "message": "Password changed successfully"
        }
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    data = _parse_json_body(request)
    new_password = data.get('new_password', '').strip()
    
    if not new_password or len(new_password) < 8:
        return JsonResponse({
            'success': False,
            'error': 'New password must be at least 8 characters'
        }, status=400)
    
    try:
        service = _get_identity_service()
        async_to_sync(service.change_password)(
            email=request.user.email,
            new_password=new_password
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Password changed successfully'
        }, status=200)
        
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
