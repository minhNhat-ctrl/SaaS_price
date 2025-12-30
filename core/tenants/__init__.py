"""
Tenants Module - Multi-tenant Foundation for SaaS Platform

Cấu trúc:
- domain/: Entity, Value Object, Exception cho tenant (không import Django)
- services/: Use-case, business logic (không import Django, request, response)
- repositories/: Interface truy cập dữ liệu
- infrastructure/: Django ORM, API Views, Middleware
"""
