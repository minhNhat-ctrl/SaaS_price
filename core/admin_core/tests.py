"""
Integration tests cho Admin Core
"""
import pytest
from core.admin_core.services import AdminHashService
from core.admin_core.domain import AdminSecurityError, InvalidAdminHashError


class TestAdminHashService:
    """Test admin hash service"""

    def test_generate_hash(self):
        """Test tạo hash"""
        service = AdminHashService()
        hash1 = service.generate_hash()
        
        assert hash1 is not None
        assert len(hash1) == 32  # 16 bytes = 32 hex chars
        assert service.get_hash() == hash1

    def test_validate_hash_success(self):
        """Test validate hash đúng"""
        service = AdminHashService()
        hash_val = service.generate_hash()
        
        is_valid = service.validate_hash(hash_val)
        assert is_valid is True

    def test_validate_hash_failure(self):
        """Test validate hash sai"""
        service = AdminHashService()
        service.generate_hash()
        
        is_valid = service.validate_hash("wrong_hash_value")
        assert is_valid is False

    def test_rate_limiting(self):
        """Test rate limiting"""
        service = AdminHashService(secret_key="test")
        service.generate_hash()
        
        client_ip = "192.168.1.1"
        
        # Multiple failed attempts
        for i in range(5):
            service.validate_hash("wrong", client_ip)
        
        # 6th attempt bị block
        with pytest.raises(AdminSecurityError):
            service.validate_hash("wrong", client_ip)

    def test_get_admin_url(self):
        """Test generate admin URL"""
        service = AdminHashService()
        service.generate_hash()
        
        url = service.get_admin_url(base_url="https://example.com")
        assert url.startswith("https://example.com/admin/")
        assert len(url.split('/')[-2]) == 32  # Hash length


class TestAdminModuleLoader:
    """Test admin module loader"""

    @pytest.mark.asyncio
    async def test_discover_modules(self):
        """Test discover modules"""
        from core.admin_core.services import AdminModuleLoader
        
        loader = AdminModuleLoader()
        
        # This will scan platform/ directory
        # and load modules with infrastructure/django_admin.py
        # For now, this is a placeholder test
        
        modules = await loader.discover_and_load_modules()
        assert isinstance(modules, list)
