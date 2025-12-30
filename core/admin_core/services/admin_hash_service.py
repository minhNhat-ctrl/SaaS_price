"""
Admin Hash Service - Tạo và quản lý hash URL

Mục đích:
- Tạo hash URL ngẫu nhiên cho admin
- Lấy hash hiện tại
- So sánh hash (constant-time)

Nguyên tắc:
- Service KHÔNG import Django
- Service KHÔNG validate hash (điều đó là AdminService)
- Service KHÔNG quản lý rate limiting (điều đó là AdminService)
- Service chỉ handle hash generation & comparison

Lợi ích:
- Tách rõ concerns (hash generation vs validation logic)
- Dễ test
- AdminService điều phối security policy
"""
import secrets
import hmac
from typing import Optional


class AdminHashService:
    """
    Service để quản lý hash URL (thuần tuý)
    
    Trách nhiệm:
    - Generate hash random
    - Lấy hash hiện tại
    - So sánh hash với constant-time
    
    KHÔNG trách nhiệm:
    - Validate (AdminService)
    - Rate limiting (AdminService)
    - Exception handling (caller quyết định)
    """

    def __init__(self, secret_key: str = None):
        """
        Initialize service
        
        Args:
            secret_key: Dùng cho HMAC (không bắt buộc)
        """
        self.secret_key = secret_key or secrets.token_hex(32)
        self.admin_hash: Optional[str] = None

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

    def constant_time_compare(self, provided_hash: str, expected_hash: str) -> bool:
        """
        So sánh hash với constant time (chống timing attack)
        
        Args:
            provided_hash: Hash từ input
            expected_hash: Hash mong đợi
        
        Returns:
            True nếu giống, False nếu khác
        """
        return hmac.compare_digest(provided_hash, expected_hash)

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
