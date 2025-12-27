"""
Admin Core Module - Central Admin Management for SaaS Platform

Mục đích:
- Cung cấp base admin site cho tất cả modules
- Auto-load django_admin.py từ các modules
- Bảo vệ admin URL bằng hash + rate limiting (chống brute force)
- Quản lý và kiểm tra mọi chức năng của modules

Kiến trúc:
- domain/: AdminModule entity, exceptions
- services/: AdminModuleLoader (scan & load modules)
- infrastructure/: Middleware, Custom AdminSite, URL config
"""
