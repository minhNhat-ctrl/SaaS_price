"""
Admin Core Documentation

Module admin_core là trung tâm quản lý hệ thống, cung cấp:
1. Protected admin interface (bằng hash URL)
2. Auto-load django_admin.py từ các modules
3. Rate limiting & anti-brute force protection
4. Module discovery & management
"""

# ============================================================================
# 1. CÁCH SỬ DỤNG
# ============================================================================

# Khởi động server:
#   python manage.py runserver
#
# Admin URL sẽ được in ra console:
#   [ADMIN URL] http://localhost:8000/admin/{hash}/
#
# Copy & paste hash này vào browser để truy cập admin

# ============================================================================
# 2. KIẾN TRÚC ADMIN CORE
# ============================================================================

# domain/
#   - admin_module.py:      AdminModule entity (đại diện module)
#   - exceptions.py:        Domain exceptions (không import Django)
#
# services/
#   - admin_module_loader.py: Service auto-load django_admin.py từ modules
#   - admin_hash_service.py:  Service quản lý hash URL, rate limiting
#
# infrastructure/
#   - custom_admin.py:      Custom AdminSite với auto-load modules
#   - security_middleware.py: Middleware validate hash, rate limiting
#   - urls.py:              URL config
#   - apps.py:              App configuration
#
# tests.py:                 Unit tests


# ============================================================================
# 3. NGUYÊN TẮC HOẠT ĐỘNG
# ============================================================================

# A. Hash URL Protection
# ==================
# 
# Admin URL được bảo vệ bằng hash ngẫu nhiên:
# - /admin/{hash}/ → truy cập được
# - /admin/        → 404 (hoặc redirect to hash)
# - /admin/xyz/    → 403 Forbidden (invalid hash)
#
# Hash được generate khi server start, lưu tại:
# - Django settings.ADMIN_HASH_SERVICE
# - In ra console (development)
# - Có thể lưu ở environment variable (production)

# B. Rate Limiting (Anti Brute Force)
# ===================================
#
# Invalid hash attempts bị track:
# - Max 5 failed attempts
# - Lockout 30 minutes
# - Per client IP
# - Response: {"error": "...", "failed_attempts": X, "max_attempts": 5}

# C. Module Auto-Load
# ===================
#
# Admin Core tự động:
# 1. Scan platform/ directory
# 2. Tìm tất cả infrastructure/django_admin.py
# 3. Import & register ModelAdmin
# 4. Không cần edit admin core khi thêm module
#
# Ví dụ:
#   platform/tenants/infrastructure/django_admin.py
#   → Auto-load khi Django start
#   → Models appear ở admin interface


# ============================================================================
# 4. THĠ ĐỀ THÊM MODULE MỚI
# ============================================================================

# Bước 1: Tạo module (ví dụ: subscriptions)
#   mkdir platform/subscriptions
#   mkdir platform/subscriptions/infrastructure

# Bước 2: Tạo infrastructure/django_admin.py
#   touch platform/subscriptions/infrastructure/django_admin.py
#
#   Nội dung:
#   ```python
#   from django.contrib import admin
#   from .django_models import Subscription
#
#   @admin.register(Subscription)
#   class SubscriptionAdmin(admin.ModelAdmin):
#       list_display = ['tenant', 'plan', 'status']
#   ```

# Bước 3: Thêm vào INSTALLED_APPS (config/settings.py)
#   'core.subscriptions.apps.SubscriptionsConfig',

# Bước 4: Admin interface sẽ tự động có models từ module này
#   Không cần edit admin core!


# ============================================================================
# 5. SECURITY BEST PRACTICES
# ============================================================================

# Production:
# ===========
# 
# 1. Set hash ở environment variable:
#    os.environ.get('ADMIN_HASH', admin_hash_service.generate_hash())
#
# 2. Disable standard /admin/ URL:
#    # path('admin/', admin.site.urls),  # Comment out
#
# 3. Enable HTTPS only:
#    SESSION_COOKIE_SECURE = True
#    CSRF_COOKIE_SECURE = True
#
# 4. Restrict admin access by IP:
#    Add ALLOWED_ADMIN_IPS setting
#
# 5. Enable admin logs:
#    Implement logging middleware để track admin access

# Development:
# ============
#
# Hash được in ở console, OK để dùng
# Enable DEBUG = True (nhưng không phải production!)


# ============================================================================
# 6. TÍCH HỢP VỚI TENANT MIDDLEWARE
# ============================================================================

# Admin interface KHÔNG phụ thuộc tenant
# Admin có thể:
# - Quản lý tất cả tenants
# - View all data across tenants
# - Manage subscriptions, billing, etc.

# Luồng request:
#
# HTTP Request /admin/{hash}/
#   ↓
# AdminSecurityMiddleware (validate hash)
#   ↓
# TenantMiddleware (skip cho admin URLs)
#   ↓
# Django Admin View


# ============================================================================
# 7. DEBUGGING & TROUBLESHOOTING
# ============================================================================

# Hash not showing in console?
# ============================
# - Check logs: grep "ADMIN URL" 
# - Check settings: python manage.py shell
#   >>> from django.conf import settings
#   >>> settings.ADMIN_HASH_SERVICE.get_hash()

# Invalid hash errors?
# ====================
# - Verify hash giống nhau (không thay đổi khi reload page)
# - Check middleware order (AdminSecurityMiddleware phải ở cuối)
# - Check IP tracking (proxy, VPN có thể cause issues)

# Rate limited?
# =============
# - Reset via: settings.ADMIN_HASH_SERVICE.reset_failed_attempts(ip)
# - Check failed attempts: settings.ADMIN_HASH_SERVICE.get_failed_attempts_for_ip(ip)

# Module not loading?
# ===================
# - Check django_admin.py exists ở infrastructure/
# - Check models được import đúng
# - Check INSTALLED_APPS có module apps.py
# - Run: python manage.py shell
#   >>> from core.admin_core.services import AdminModuleLoader
#   >>> loader = AdminModuleLoader()
#   >>> failed = await loader.discover_and_load_modules()


# ============================================================================
# 8. CUSTOM SETTINGS
# ============================================================================

# config/settings.py:
#
# # Enable/disable hash protection
# ADMIN_ENABLE_HASH = True
#
# # Hash service instance
# ADMIN_HASH_SERVICE = AdminHashService(secret_key=SECRET_KEY)
#
# # Custom allowed IPs (optional)
# ALLOWED_ADMIN_IPS = ['127.0.0.1', '192.168.1.0/24']


# ============================================================================
# 9. API USAGE EXAMPLES
# ============================================================================

# Get admin URL:
# from core.admin_core.services import AdminHashService
# service = AdminHashService()
# url = service.get_admin_url(base_url='https://example.com')
# # Output: https://example.com/admin/{hash}/

# Validate hash:
# is_valid = service.validate_hash(user_hash, client_ip='192.168.1.1')

# List loaded modules:
# from core.admin_core.services import AdminModuleLoader
# loader = AdminModuleLoader()
# modules = await loader.discover_and_load_modules()
# for mod in modules:
#     print(f"{mod.name}: {mod.models}")
