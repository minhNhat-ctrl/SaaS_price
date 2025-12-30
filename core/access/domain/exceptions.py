"""
Domain Exceptions for Access Module

Custom exceptions for authorization and RBAC operations.
"""


class AccessException(Exception):
    """Base exception for access module."""
    pass


class MembershipException(AccessException):
    """Base exception for membership operations."""
    pass


class MembershipAlreadyExistsError(MembershipException):
    """Raised when membership already exists."""
    def __init__(self, user_id: str, tenant_id: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        super().__init__(f"Membership already exists for user {user_id} in tenant {tenant_id}")


class MembershipNotFoundError(MembershipException):
    """Raised when membership is not found."""
    def __init__(self, user_id: str, tenant_id: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        super().__init__(f"Membership not found for user {user_id} in tenant {tenant_id}")


class RoleException(AccessException):
    """Base exception for role operations."""
    pass


class RoleNotFoundError(RoleException):
    """Raised when role is not found."""
    def __init__(self, role_id: str):
        self.role_id = role_id
        super().__init__(f"Role not found: {role_id}")


class RoleAlreadyExistsError(RoleException):
    """Raised when role already exists."""
    def __init__(self, role_name: str):
        self.role_name = role_name
        super().__init__(f"Role already exists: {role_name}")


class PermissionException(AccessException):
    """Base exception for permission operations."""
    pass


class PermissionNotFoundError(PermissionException):
    """Raised when permission is not found."""
    def __init__(self, permission_id: str):
        self.permission_id = permission_id
        super().__init__(f"Permission not found: {permission_id}")


class PermissionDeniedError(PermissionException):
    """Raised when permission is denied."""
    def __init__(self, user_id: str, resource: str, action: str):
        self.user_id = user_id
        self.resource = resource
        self.action = action
        super().__init__(f"Permission denied: user {user_id} cannot {action} on {resource}")


class PolicyException(AccessException):
    """Base exception for policy operations."""
    pass


class PolicyViolationError(PolicyException):
    """Raised when policy is violated."""
    def __init__(self, policy_name: str, reason: str):
        self.policy_name = policy_name
        self.reason = reason
        super().__init__(f"Policy '{policy_name}' violated: {reason}")
