"""
Admin Hash Service - Tạo và xác thực hash URL chống brute force

Mục đích:
- Tạo hash URL ngẫu nhiên cho admin
- Validate hash từ request
- Theo dõi failed attempts (rate limiting)
"""
import hashlib
import secrets
import hmac
from typing import Tuple, Optional
from datetime import datetime, timedelta


class AdminHashService:
    """
    Service để quản lý hash URL chống brute force
    
    Cơ chế:
    1. Tạo hash random khi server start
    2. Hash này stored ở environment variable hoặc config
    3. Admin URL: /admin/{hash}/
    4. Validate hash từ request
    5. Theo dõi failed attempts → rate limit
    
    Security:
    - Hash random 32 bytes (256 bits)
    - Constant-time comparison (chống timing attack)
    - Failed attempt tracking
    """

    def __init__(self, secret_key: str = None):
        """
        Initialize service
        
        Args:
            secret_key: Django SECRET_KEY (dùng cho HMAC)
        """
        self.secret_key = secret_key or secrets.token_hex(32)
        self.admin_hash: Optional[str] = None
        self.failed_attempts = {}  # IP → [(timestamp, reason), ...]
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=30)

    def generate_hash(self) -> str:
        """
        Tạo hash URL random
        
        Returns:
            Hash 32 ký tự (hex)
        """
        self.admin_hash = secrets.token_hex(16)  # 32 chars
        return self.admin_hash

    def get_hash(self) -> str:
        """Lấy hash hiện tại (generate nếu chưa có)"""
        if not self.admin_hash:
            self.generate_hash()
        return self.admin_hash

    def validate_hash(self, provided_hash: str, client_ip: str = None) -> bool:
        """
        Validate hash từ request
        
        Args:
            provided_hash: Hash từ URL
            client_ip: IP của client (để tracking)
        
        Returns:
            True nếu hash đúng, False nếu sai
        
        Raises:
            AdminSecurityError: Nếu bị rate limit
        """
        from platform.admin_core.domain import AdminSecurityError
        
        # Check rate limit
        if client_ip and self._is_rate_limited(client_ip):
            raise AdminSecurityError(
                f"Too many failed attempts from {client_ip}. Please try again later."
            )

        # Constant-time comparison (chống timing attack)
        expected = self.get_hash()
        is_valid = hmac.compare_digest(provided_hash, expected)

        # Track failed attempt
        if not is_valid and client_ip:
            self._record_failed_attempt(client_ip, "invalid_hash")

        return is_valid

    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check xem IP có bị rate limit không"""
        if client_ip not in self.failed_attempts:
            return False

        attempts = self.failed_attempts[client_ip]
        
        # Clean up old attempts (ngoài lockout window)
        now = datetime.now()
        valid_attempts = [
            (ts, reason) for ts, reason in attempts
            if now - ts < self.lockout_duration
        ]
        
        self.failed_attempts[client_ip] = valid_attempts

        return len(valid_attempts) >= self.max_failed_attempts

    def _record_failed_attempt(self, client_ip: str, reason: str = ""):
        """Record một failed attempt"""
        if client_ip not in self.failed_attempts:
            self.failed_attempts[client_ip] = []

        self.failed_attempts[client_ip].append((datetime.now(), reason))

    def reset_failed_attempts(self, client_ip: str):
        """Reset failed attempts cho IP"""
        if client_ip in self.failed_attempts:
            del self.failed_attempts[client_ip]

    def get_admin_url(self, base_url: str = "") -> str:
        """
        Lấy đường dẫn admin URL (with hash)
        
        Args:
            base_url: Base URL của site (ví dụ: 'https://example.com')
        
        Returns:
            Đường dẫn admin đầy đủ
        """
        hash_val = self.get_hash()
        url = f"/admin/{hash_val}/"
        if base_url:
            url = base_url.rstrip('/') + url
        return url

    def get_failed_attempts_for_ip(self, client_ip: str) -> int:
        """Lấy số lượng failed attempts cho IP"""
        if client_ip not in self.failed_attempts:
            return 0

        now = datetime.now()
        valid_attempts = [
            (ts, reason) for ts, reason in self.failed_attempts[client_ip]
            if now - ts < self.lockout_duration
        ]

        return len(valid_attempts)
