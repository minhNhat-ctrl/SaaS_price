"""
Domain Exceptions - Admin Core (chỉ business logic, không import Django)
"""


class AdminException(Exception):
    """Base exception cho admin core"""
    pass


class AdminModuleNotFoundError(AdminException):
    """Module admin không tìm thấy"""
    def __init__(self, module_name: str):
        super().__init__(f"Admin module '{module_name}' not found")


class AdminSecurityError(AdminException):
    """Lỗi bảo mật admin (rate limit, invalid hash, etc.)"""
    def __init__(self, message: str):
        super().__init__(message)


class InvalidAdminHashError(AdminException):
    """Hash URL admin không hợp lệ"""
    def __init__(self, hash_value: str = None):
        message = "Invalid admin hash"
        if hash_value:
            message += f": {hash_value}"
        super().__init__(message)


class AdminModuleLoadError(AdminException):
    """Lỗi load module admin"""
    def __init__(self, module_name: str, reason: str):
        super().__init__(f"Failed to load admin module '{module_name}': {reason}")
