# Tenant Multi-tenancy Migration Guide

## Mô hình: Shared Database + Separate Schemas (Schema-per-Tenant)

### Kiến trúc

```
Database: pricesync_saas
├── public schema (shared)
│   ├── tenants (Tenant models)
│   ├── tenant_domains (Domain mapping)
│   └── admin tables (shared)
│
├── tenant_acme schema (Acme Inc.)
│   ├── products
│   ├── price_history
│   ├── users
│   └── subscriptions
│
└── tenant_globex schema (Globex Corp.)
    ├── products
    ├── price_history
    ├── users
    └── subscriptions
```

---

## Setup Django-Tenants

### 1. Install package

```bash
pip install django-tenants==3.5.0
```

### 2. Configure settings.py

```python
# settings.py

INSTALLED_APPS = [
    # ...
    'django_tenants',  # Đặt trước các app khác
    'core.tenants',
    'core.admin_core',
    # ...
]

MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',  # Đặt đầu tiên
    'core.tenants.infrastructure.middleware.TenantMiddleware',
    # ... các middleware khác
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',  # Quan trọng!
        'NAME': 'pricesync_saas',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Multi-tenancy configuration
TENANT_MODEL = 'tenants.Tenant'
TENANT_DOMAIN_MODEL = 'tenants.Domain'
```

---

## Migration Strategy

### A. Initial Setup (lần đầu tiên)

#### Step 1: Create public schema tables

```bash
# Migrate shared tables (public schema)
python manage.py migrate_schemas --shared

# Output:
# Running migrations for schema 'public'...
# ✓ Migrated tenants
# ✓ Migrated auth
# ✓ Migrated admin
# etc.
```

Bây giờ `public` schema có:
- `tenants_tenant`
- `tenants_domain`
- `auth_user`
- `django_admin_log`
- etc.

#### Step 2: Kiểm tra database

```bash
psql -d pricesync_saas

# Check schemas
\dn
# Result:
# Name     | Owner
# ----------|-------
# public   | postgres
```

### B. Create Tenant + Auto-migrate

#### Step 1: Create tenant (via service hoặc API)

```python
# Python shell
python manage.py shell

from core.tenants.services import TenantService
from core.tenants.repositories import DjangoTenantRepository

repo = DjangoTenantRepository()
service = TenantService(repo)

# Tạo tenant
tenant = asyncio.run(service.create_tenant(
    name='Acme Inc.',
    slug='acme',
    domain='acme.example.com'
))

# Output:
# ✓ Tenant created: Acme Inc. (slug=acme, schema=tenant_acme)
```

Lúc này:
- `public.tenants_tenant` có record: (id, name='Acme Inc.', slug='acme', schema_name='tenant_acme')
- `public.tenants_domain` có record: (domain='acme.example.com', tenant_id=...)
- Schema `tenant_acme` được tạo tự động (trống)

#### Step 2: Migrate tenant-specific tables

```bash
# Migrate cho tenant cụ thể
python manage.py migrate --tenant=acme

# Output:
# Running migrations for schema 'tenant_acme'...
# ✓ Migrated products_0001
# ✓ Migrated prices_0001
# etc.
```

Bây giờ `tenant_acme` schema có:
- `products_product`
- `prices_price_history`
- `subscriptions_subscription`
- etc.

#### Step 3: Migrate all tenants cùng lúc

```bash
# Migrate shared schema
python manage.py migrate_schemas --shared

# Migrate tất cả tenant schemas
python manage.py migrate_schemas

# Output:
# Running migrations for schema 'public'...
# ✓ Done

# Running migrations for schema 'tenant_acme'...
# ✓ Done

# Running migrations for schema 'tenant_globex'...
# ✓ Done
```

---

## Workflow Thực tế

### Scenario 1: Thêm tenant mới

```bash
# 1. Tạo tenant (auto-create schema + migrate)
python manage.py create_tenant \
  --name='Globex Corp.' \
  --slug='globex' \
  --domain='globex.example.com'

# Or via service:
asyncio.run(service.create_tenant(
    name='Globex Corp.',
    slug='globex',
    domain='globex.example.com'
))

# 2. Verify schema created
psql -d pricesync_saas
\dn
# Result:
# Name        | Owner
# ------------|-------
# public      | postgres
# tenant_acme | postgres
# tenant_globex | postgres
```

### Scenario 2: Thêm model/field mới

```bash
# 1. Tạo migration (ở shared migrations)
python manage.py makemigrations products

# 2. Migrate shared schema
python manage.py migrate_schemas --shared

# 3. Migrate tất cả tenant schemas
python manage.py migrate_schemas --tenant=acme
python manage.py migrate_schemas --tenant=globex

# Hoặc 1 lệnh
python manage.py migrate_schemas
```

### Scenario 3: Query data của tenant

```python
from django_tenants.utils import tenant_context
from core.tenants.infrastructure.django_models import Tenant as TenantModel
from products.models import Product

# Switch schema & query
acme_tenant = TenantModel.objects.get(slug='acme')

with tenant_context(acme_tenant):
    # Tất cả queries sẽ dùng schema 'tenant_acme'
    products = Product.objects.all()  # From tenant_acme schema
    print(f"Acme products: {len(products)}")

globex_tenant = TenantModel.objects.get(slug='globex')

with tenant_context(globex_tenant):
    # Switch sang tenant_globex
    products = Product.objects.all()  # From tenant_globex schema
    print(f"Globex products: {len(products)}")
```

### Scenario 4: Drop schema (hard delete)

```sql
-- Manual drop schema
DROP SCHEMA tenant_acme CASCADE;

-- Hoặc command
python manage.py drop_schema --tenant=acme
```

---

## Debugging

### Check current schema

```python
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT current_schema();")
    print(cursor.fetchone()[0])  # 'public' hoặc 'tenant_acme'
```

### Check all schemas

```bash
psql -d pricesync_saas -c "\dn"
```

### Check tenant record

```bash
psql -d pricesync_saas

SELECT id, name, slug, schema_name FROM tenants_tenant;
```

### Check domain mapping

```bash
psql -d pricesync_saas

SELECT domain, tenant_id FROM tenants_domain;
```

---

## Common Commands

```bash
# Migrate shared schema
python manage.py migrate_schemas --shared

# Migrate specific tenant
python manage.py migrate_schemas --tenant=acme

# Migrate all tenants
python manage.py migrate_schemas

# Create superuser in specific tenant
python manage.py createsuperuser --tenant=acme

# Shell with tenant context
python manage.py shell --tenant=acme

# List all tenants
python manage.py list_tenants

# Drop schema
python manage.py drop_schema --tenant=acme --force
```

---

## Architecture Compliance

### DDD Principles

✓ **Domain**: Tenant entity không import Django
✓ **Repository**: Handle schema switching (via django-tenants)
✓ **Service**: Điều phối logic, không biết schema details
✓ **Infrastructure**: Middleware + Django-Tenants integration

### Flow

```
HTTP Request (domain=acme.example.com)
    ↓
TenantMiddleware (resolve domain → tenant)
    ↓
Django-Tenants Middleware (set schema='tenant_acme')
    ↓
TenantService (async operations)
    ↓
Repository (query with schema context)
    ↓
ORM Queries (tự động dùng tenant_acme schema)
    ↓
Response
```

---

## Performance Notes

1. **Schema isolation**: Mỗi tenant hoàn toàn tách biệt
2. **Query efficiency**: Các query chỉ scan một schema
3. **Migration time**: Parallel migrate (tools: Django-Tenants + Celery)
4. **Backup**: Per-schema backup strategy

---

## Troubleshooting

### Issue: "relation does not exist"

**Cause**: Schema chưa migrate
**Fix**:
```bash
python manage.py migrate --tenant=acme
```

### Issue: "no schema has been set"

**Cause**: Không set schema context
**Fix**:
```python
from django_tenants.utils import tenant_context

tenant = Tenant.objects.get(slug='acme')
with tenant_context(tenant):
    # queries here
```

### Issue: "UNIQUE constraint violation"

**Cause**: Data duplicate trong schema
**Fix**: Check migrations & seeders

---

## Next Steps

1. ✓ Setup Django-Tenants
2. ✓ Configure settings.py
3. ✓ Implement TenantMiddleware
4. ✓ Create initial migration
5. Create first tenant
6. Implement multi-tenant API views
7. Setup Celery for async tasks (per-tenant)
8. Implement tenant billing/subscription logic

