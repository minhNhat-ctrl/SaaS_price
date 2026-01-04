"""
Admin Security Middleware - Chống brute force, validate hash

Middleware này:
1. Intercept requests tới /admin/{hash}/
2. Gọi AdminService để validate hash
3. Rate limit invalid attempts
4. Return 403 nếu invalid

Nguyên tắc:
- Gọi AdminService (không gọi AdminHashService trực tiếp)
- Infrastructure layer chỉ handle HTTP details
- Service layer điều phối business logic
"""
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.conf import settings
import re
import logging

from core.admin_core.domain import AdminSecurityError

logger = logging.getLogger(__name__)


class AdminSecurityMiddleware(MiddlewareMixin):
    """
    Middleware bảo vệ admin URL bằng hash + rate limiting
    
    Cấu hình:
    - ADMIN_SERVICE: Instance của AdminService (set ở apps.py)
    - ADMIN_ENABLE_HASH: Enable/disable hash protection (default: True)
    
    URL pattern: /admin/{hash}/
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # AdminService sẽ được inject ở ready() của AppConfig
        self.admin_service = None
        self.enable_hash = getattr(settings, 'ADMIN_ENABLE_HASH', True)
        super().__init__(get_response)

    def set_admin_service(self, service):
        """Set AdminService instance (called by app ready)"""
        self.admin_service = service

    def __call__(self, request):
        """Process request"""
        # Check nếu là admin path
        if self._is_admin_path(request):
            # Validate hash thông qua AdminService
            is_valid = self._validate_admin_hash(request)
            
            if not is_valid:
                return self._handle_invalid_hash(request)

        response = self.get_response(request)
        return response

    def _is_admin_path(self, request) -> bool:
        """
        Kiểm tra request có phải tới admin không.
        
        ❗ IMPORTANT: Phải exclude login/logout/static để tránh redirect loop!
        """
        path = request.path
        
        # Pattern: /admin/{hash}/ hoặc /admin/
        if not path.startswith('/admin/'):
            return False
        
        # ✅ ALLOW these paths without hash validation (avoid redirect loop)
        excluded_paths = [
            '/admin/login/',
            '/admin/logout/',
            '/admin/jsi18n/',  # Django i18n JS
            '/admin/static/',   # Static files
        ]
        
        for excluded in excluded_paths:
            if excluded in path:
                return False
        
        # Also check for hash-based admin paths like /admin/secure-admin-2025/login/
        # Extract pattern: /admin/{hash}/login/ → should be allowed
        import re
        if re.match(r'^/admin/[^/]+/(login|logout|jsi18n)', path):
            return False
        
        return True

    def _validate_admin_hash(self, request) -> bool:
        """
        Validate hash từ URL
        
        Format: /admin/{hash}/
        Gọi AdminService để validate (+ rate limiting)
        """
        if not self.enable_hash:
            # Hash check disabled
            return True

        if not self.admin_service:
            logger.error("AdminService not initialized in middleware")
            return False

        path = request.path
        # Extract hash từ path: /admin/{hash}/ → hash
        match = re.match(r'^/admin/([a-f0-9]+)/', path)
        
        if not match:
            # /admin/ mà không có hash → invalid
            logger.warning(f"Admin access without hash: {path}")
            return False

        provided_hash = match.group(1)
        client_ip = self._get_client_ip(request)

        try:
            # Gọi AdminService (không gọi AdminHashService trực tiếp)
            # AdminService sẽ handle rate limiting + validation
            import asyncio
            is_valid = asyncio.run(
                self.admin_service.validate_admin_hash(provided_hash, client_ip)
            )
            return is_valid
        except AdminSecurityError as e:
            logger.warning(f"Admin security error from {client_ip}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating admin hash: {str(e)}")
            return False

    def _handle_invalid_hash(self, request):
        """Handle invalid hash"""
        client_ip = self._get_client_ip(request)
        
        if not self.admin_service:
            failed_count = 0
            max_attempts = 5
        else:
            failed_count = self.admin_service.get_failed_attempts_for_ip(client_ip)
            max_attempts = self.admin_service.max_failed_attempts

        logger.warning(
            f"Invalid admin hash attempt from {client_ip} "
            f"(failed: {failed_count}/{max_attempts})"
        )

        return JsonResponse(
            {
                "error": "Invalid admin hash",
                "failed_attempts": failed_count,
                "max_attempts": max_attempts,
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
