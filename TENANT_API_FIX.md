# Tenant API - Kiểm Tra và Sửa Lỗi

## Vấn đề

API endpoints cho add, update, delete tenants báo lỗi HTTP 500.

## Nguyên nhân

Migration `0005_add_url_hash_manual.py` trong Products module có vấn đề:
- Kiểm tra column tồn tại trong schema `public` cố định
- Khi tạo tenant mới, django-tenants auto-run migrations vào schema của tenant (ví dụ: `tenant_test_ca3eeaaa`)
- Migration check sai schema → luôn cố add column đã tồn tại → lỗi `ProgrammingError: column "url_hash" already exists`

## Giải pháp

Sửa migration để check schema hiện tại thay vì hardcode 'public':

```sql
-- Trước (SAI)
WHERE table_schema='public'

-- Sau (ĐÚNG)  
WHERE table_schema=current_schema()
```

## Các thay đổi

### 1. Fixed Migration
**File:** `services/products/migrations/0005_add_url_hash_manual.py`

- Sử dụng `current_schema()` thay vì `'public'`
- Tách riêng check cho column và indexes
- Đảm bảo idempotent (chạy nhiều lần không lỗi)

### 2. Updated Settings
**File:** `config/settings.py`

- Thêm `'testserver'` vào `ALLOWED_HOSTS` để support Django test client

### 3. Created Test Scripts

**Python Test Client:** `test_tenant_api_client.py`
```bash
python3.9 manage.py shell < test_tenant_api_client.py
```

**Bash/curl Test:** `test_tenant_api.sh`
```bash
./test_tenant_api.sh
```

## Kết quả kiểm tra

### ✓ Test Service Layer

```python
# Create tenant
tenant = async_to_sync(service.create_tenant)(
    name='Test Tenant',
    slug='test-tenant-123',
    domain='test123.example.com'
)
# ✓ SUCCESS

# Update tenant
updated = async_to_sync(service.update_tenant_info)(
    tenant_id=tenant_id,
    name='Updated Name'
)
# ✓ SUCCESS

# Delete tenant  
result = async_to_sync(service.delete_tenant)(tenant_id)
# ✓ SUCCESS
```

### ✓ Test API Endpoints

```bash
# GET /api/tenants/
Status: 200
Success: True

# POST /api/tenants/
Status: 201
Success: True
Created Tenant ID: 3695e7c5-3475-49a0-ba64-cb778e1763c7

# GET /api/tenants/{id}/
Status: 200
Success: True

# PATCH /api/tenants/{id}/
Status: 200
Success: True
New name: Updated Tenant Name

# DELETE /api/tenants/{id}/
Status: 200
Success: True
Message: Tenant deleted successfully
```

## Trạng thái

✅ **HOÀN THÀNH** - Tất cả API endpoints hoạt động chính xác:
- ✅ POST /api/tenants/ - Create tenant (auto-create schema + membership)
- ✅ GET /api/tenants/ - List tenants
- ✅ GET /api/tenants/{id}/ - Get tenant details
- ✅ PATCH/PUT /api/tenants/{id}/ - Update tenant
- ✅ DELETE /api/tenants/{id}/ - Delete tenant (soft delete)
- ✅ POST /api/tenants/{id}/activate/ - Activate tenant
- ✅ POST /api/tenants/{id}/suspend/ - Suspend tenant
- ✅ POST /api/tenants/{id}/add-domain/ - Add domain

## Notes

### Multi-tenant Migration Flow
1. User tạo tenant via API
2. Django ORM save Tenant model  
3. django-tenants hook vào save() → auto-create schema
4. django-tenants auto-run migrations vào tenant schema
5. Migration `0005` check column exists trong `current_schema()`
6. Nếu column chưa có → create, nếu có rồi → skip
7. Schema tenant hoàn tất

### Security
- API requires authentication (`@login_required_api`)
- Auto-create admin membership cho tenant creator
- Membership activated ngay lập tức (không cần accept invitation)
- List tenants only returns tenants where user has membership

### Testing
Để test nhanh:
```bash
cd /var/www/PriceSynC/Saas_app
python3.9 manage.py shell < test_tenant_api_client.py
```

## Cấu trúc API

```
api/tenants/
├── GET  /                    → List tenants (with membership)
├── POST /                    → Create tenant (+ auto membership)
├── GET  /{id}/              → Get tenant details
├── PATCH /{id}/             → Update tenant
├── DELETE /{id}/            → Delete tenant
├── POST /{id}/activate/     → Activate tenant
├── POST /{id}/suspend/      → Suspend tenant  
└── POST /{id}/add-domain/   → Add domain
```

## Kiến trúc

```
HTTP Request
    ↓
api_views.py (login_required_api)
    ↓
TenantService (business logic)
    ↓
DjangoTenantRepository (data access)
    ↓
Django ORM / PostgreSQL
```

---
**Updated:** 2026-01-03
**Status:** ✅ RESOLVED
