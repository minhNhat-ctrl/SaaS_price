"""
Domain Exceptions - Chỉ định nghĩa nghiệp vụ, không import Django
"""


class TenantException(Exception):
    """Base exception cho tenant domain"""
    pass


class TenantNotFoundError(TenantException):
    """Tenant không tìm thấy"""
    def __init__(self, tenant_id: str = None, slug: str = None):
        if tenant_id:
            message = f"Tenant with ID '{tenant_id}' not found"
        elif slug:
            message = f"Tenant with slug '{slug}' not found"
        else:
            message = "Tenant not found"
        super().__init__(message)


class TenantAlreadyExistsError(TenantException):
    """Tenant đã tồn tại"""
    def __init__(self, slug: str):
        super().__init__(f"Tenant with slug '{slug}' already exists")


class InvalidTenantSlugError(TenantException):
    """Slug tenant không hợp lệ"""
    def __init__(self, slug: str):
        super().__init__(f"Invalid slug '{slug}'. Slug must be lowercase alphanumeric with hyphens only")


class TenantStatusInvalidError(TenantException):
    """Trạng thái tenant không hợp lệ"""
    def __init__(self, status: str):
        super().__init__(f"Invalid status '{status}'")


class TenantDomainInvalidError(TenantException):
    """Domain tenant không hợp lệ"""
    def __init__(self, domain: str):
        super().__init__(f"Invalid domain '{domain}'")
