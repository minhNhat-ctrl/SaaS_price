"""
Access Module - Authorization & RBAC for SaaS Platform

Central authorization system managing:
- Membership: User-Tenant relationships
- Roles: Role definitions and assignments
- Permissions: Granular access control
- Policy: Authorization policies

Architecture:
- domain/: Pure business entities (Membership, Role, Permission, Policy)
- services/: Authorization use cases (grant, revoke, check permissions)
- repositories/: Data access interfaces
- infrastructure/: Django ORM, API, middleware

Note: Completely independent from Django admin-core User/Group system.
"""
