"""
Repositories Layer - Data Access Interface

Định nghĩa interface để truy cập tenant data
Không chứa logic, chỉ là "cầu nối" giữa domain và infrastructure
"""
from .tenant_repo import TenantRepository

__all__ = ["TenantRepository"]
