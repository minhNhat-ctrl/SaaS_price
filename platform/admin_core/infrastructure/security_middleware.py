"""
Admin Security Middleware - Chống brute force, validate hash

Middleware này:
1. Intercept requests tới /admin/{hash}/
2. Validate hash
3. Rate limit invalid attempts
4. Log security events
"""
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse, HttpResponseForbidden
from django.conf import settings
import re

from platform.admin_core.domain import AdminSecurityError, InvalidAdminHashError
from platform.admin_core.services import AdminHashService


class AdminSecurityMiddleware(MiddlewareMixin):
    """
    Middleware bảo vệ admin URL bằng hash + rate limiting
    
    Cấu hình:
    - ADMIN_HASH_SERVICE: Instance của AdminHashService
    - ADMIN_ENABLE_HASH: Enable/disable hash protection (default: True)
    
    URL pattern: /admin/{hash}/
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_hash_service = getattr(
            settings,
            'ADMIN_HASH_SERVICE',
            AdminHashService(secret_key=settings.SECRET_KEY)
        )
        self.enable_hash = getattr(settings, 'ADMIN_ENABLE_HASH', True)
        super().__init__(get_response)

    def __call__(self, request):
        """Process request"""
        # Check nếu là admin path
        if self._is_admin_path(request):
            # Validate hash
            is_valid = self._validate_admin_hash(request)
            
            if not is_valid:
                return self._handle_invalid_hash(request)

        response = self.get_response(request)
        return response

    def _is_admin_path(self, request) -> bool:
        """Kiểm tra request có phải tới admin không"""
        path = request.path
        # Pattern: /admin/{hash}/ hoặc /admin/
        return path.startswith('/admin/')

    def _validate_admin_hash(self, request) -> bool:
        """
        Validate hash từ URL
        
        Format: /admin/{hash}/
        """
        if not self.enable_hash:
            # Hash check disabled
            return True

        path = request.path
        # Extract hash từ path: /admin/{hash}/ → hash
        match = re.match(r'^/admin/([a-f0-9]+)/', path)
        
        if not match:
            # /admin/ mà không có hash → invalid
            return False

        provided_hash = match.group(1)
        client_ip = self._get_client_ip(request)

        try:
            return self.admin_hash_service.validate_hash(provided_hash, client_ip)
        except AdminSecurityError:
            return False

    def _handle_invalid_hash(self, request):
        """Handle invalid hash"""
        client_ip = self._get_client_ip(request)
        failed_count = self.admin_hash_service.get_failed_attempts_for_ip(client_ip)

        return JsonResponse(
            {
                "error": "Invalid admin hash",
                "failed_attempts": failed_count,
                "max_attempts": self.admin_hash_service.max_failed_attempts,
            },
            status=403,
        )

    @staticmethod
    def _get_client_ip(request) -> str:
        """Extract client IP từ request"""
        # Check X-Forwarded-For (proxy)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()

        # Fallback: REMOTE_ADDR
        return request.META.get('REMOTE_ADDR', '')
