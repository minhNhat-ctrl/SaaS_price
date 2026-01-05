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
        
        # Specify backend when logging in (required when multiple backends configured)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
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
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ============================================================
# Email Verification Endpoints
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def request_email_verification_view(request):
    """
    Request email verification link.
    
    POST /api/identity/request-email-verification/
    Body: {
        "email": "user@example.com"
    }
    
    Returns:
        200: {
            "success": true,
            "message": "Verification email sent"
        }
    """
    data = _parse_json_body(request)
    email = data.get('email', '').strip()
    
    if not email:
        return JsonResponse({
            'success': False,
            'error': 'Email is required'
        }, status=400)
    
    try:
        service = _get_identity_service()
        result = async_to_sync(service.request_email_verification)(email)
        
        if result == "already_verified":
            return JsonResponse({
                'success': True,
                'message': 'Email already verified'
            }, status=200)
        
        return JsonResponse({
            'success': True,
            'message': 'Verification email sent'
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


@csrf_exempt
@require_http_methods(["POST"])
def verify_email_view(request):
    """
    Verify email using token.
    
    POST /api/identity/verify-email/
    Body: {
        "token": "verification_token"
    }
    
    Returns:
        200: {
            "success": true,
            "message": "Email verified successfully",
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
        identity = async_to_sync(service.verify_email_token)(token)
        
        return JsonResponse({
            'success': True,
            'message': 'Email verified successfully',
            'user': {
                'id': str(identity.id),
                'email': identity.email,
                'email_verified': identity.email_verified
            }
        }, status=200)
        
    except InvalidCredentialError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ============================================================
# Password Reset Endpoints
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def request_password_reset_view(request):
    """
    Request password reset link.
    
    POST /api/identity/request-password-reset/
    Body: {
        "email": "user@example.com"
    }
    
    Returns:
        200: {
            "success": true,
            "message": "Password reset email sent"
        }
    """
    data = _parse_json_body(request)
    email = data.get('email', '').strip()
    
    if not email:
        return JsonResponse({
            'success': False,
            'error': 'Email is required'
        }, status=400)
    
    try:
        service = _get_identity_service()
        async_to_sync(service.request_password_reset)(email)
        
        # Always return success for security (don't reveal if email exists)
        return JsonResponse({
            'success': True,
            'message': 'If that email exists, a password reset link has been sent'
        }, status=200)
        
    except Exception as e:
        # Still return success to avoid email enumeration
        return JsonResponse({
            'success': True,
            'message': 'If that email exists, a password reset link has been sent'
        }, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def reset_password_view(request):
    """
    Reset password using token.
    
    POST /api/identity/reset-password/
    Body: {
        "token": "reset_token",
        "new_password": "newsecurepass123"
    }
    
    Returns:
        200: {
            "success": true,
            "message": "Password reset successfully"
        }
    """
    data = _parse_json_body(request)
    token = data.get('token', '').strip()
    new_password = data.get('new_password', '').strip()
    
    if not token or not new_password:
        return JsonResponse({
            'success': False,
            'error': 'Token and new password are required'
        }, status=400)
    
    if len(new_password) < 8:
        return JsonResponse({
            'success': False,
            'error': 'Password must be at least 8 characters'
        }, status=400)
    
    try:
        service = _get_identity_service()
        identity = async_to_sync(service.reset_password_with_token)(token, new_password)
        
        return JsonResponse({
            'success': True,
            'message': 'Password reset successfully',
            'user': {
                'id': str(identity.id),
                'email': identity.email
            }
        }, status=200)
        
    except InvalidCredentialError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ============================================================
# Magic Link Login Endpoints
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def request_magic_link_view(request):
    """
    Request magic link for passwordless login.
    
    POST /api/identity/request-magic-link/
    Body: {
        "email": "user@example.com"
    }
    
    Returns:
        200: {
            "success": true,
            "message": "Magic link sent to your email"
        }
    """
    data = _parse_json_body(request)
    email = data.get('email', '').strip()
    
    if not email:
        return JsonResponse({
            'success': False,
            'error': 'Email is required'
        }, status=400)
    
    try:
        service = _get_identity_service()
        async_to_sync(service.request_magic_link)(email)
        
        return JsonResponse({
            'success': True,
            'message': 'Magic link sent to your email'
        }, status=200)
        
    except IdentityNotFoundError:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    except InvalidCredentialError as e:
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
@require_http_methods(["POST"])
def magic_link_login_view(request):
    """
    Login using magic link token.
    
    POST /api/identity/magic-login/
    Body: {
        "token": "magic_link_token"
    }
    
    Returns:
        200: {
            "success": true,
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
