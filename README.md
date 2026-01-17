```text
saas_project/
├── application/             # Lớp điều phối trung tâm (use case, orchestrator, adapter)
│   ├── dto/
│   ├── interfaces/
│   ├── orchestrators/
│   └── use_cases/
├── config/                  # Django settings & entry URLs
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                    # Các module xương sống (identity, tenants, billing, ...)
│   └── <module>/
├── services/                # Domain phụ trợ / dịch vụ mở rộng
│   └── <module>/
├── interfaces/              # Adapter chia sẻ (nếu có)
├── templates/               # Django templates dùng cho admin/backoffice
├── staticfiles/             # Static assets build sẵn
├── manage.py
└── requirement.txt
```

### 3.1 Application layer & runtime flow (điều phối trung tâm)

**Vai trò:**
- **Cổng vào duy nhất** cho mọi workflow runtime. Mọi API view (DRF, GraphQL, CLI) phải gọi qua `application.interfaces` → `application.use_cases` thay vì đi thẳng vào module.
- **Áp đặt luật nền tảng**: auto-provision tenant khi signup, đồng bộ subscription ↔ quota ↔ billing, trigger notification, ...
- **Điều phối đa module** thông qua orchestrator (saga) để đảm bảo tuần tự, retry, bù trừ khi lỗi.

**Thành phần chính:**
- `application/use_cases/`: Use case mức nền tảng. Mỗi file định nghĩa một workflow (signup, payment_capture, ...).
- `application/orchestrators/`: Tập hợp nhiều use case thành luồng dài (tenant onboarding, churn handling, ...).
- `application/interfaces/`: Adapter theo kênh (HTTP, task, scheduler) chịu trách nhiệm validate input, map DTO và trả response chuẩn.
- `application/dto/`: Định nghĩa payload/response chuẩn giữa interface ↔ use case (không trả domain entity ra ngoài).

**Nguyên tắc phụ thuộc:**
- `application` chỉ **gọi xuống** service layer của từng module (core hoặc services). Không được truy cập trực tiếp ORM hoặc infrastructure của module.
- Module **không** được import `application`. Dữ liệu/luồng chỉ chảy một chiều: API → Application → Module.
- API layer chỉ biết tới application use case. Nếu use case chỉ chạm vào một module, logic module vẫn nằm trong module service, application đóng vai trò facade.

**Luồng chuẩn mới:**
```
HTTP Request
 ↓
TenantMiddleware (resolve tenant)
 ↓
API view/adapter → Application Use Case
 ↓
Module Service → Module Repository → Domain → DB
```

**Ví dụ workflow:**
- Signup: Application use case lần lượt gọi Identity → Tenants → Subscription → Billing → Notification.
- Payment Confirmed: Application orchestrator nhận webhook, gọi Billing → Subscription → Notification.

- Mọi dữ liệu đều thuộc về tenant
- User chỉ là người dùng bên trong tenant
- ❗ Tenant KHÔNG phải User

---

## 3. Cấu trúc thư mục tổng thể

```text
saas_project/
├── application/       # Orchestrator (use_cases/orchestrators/interfaces/dto)
├── config/            # Django settings & entry URLs
├── core/              # Các module nền tảng (identity, tenants, billing, ...)
├── services/          # Module nghiệp vụ mở rộng
├── interfaces/        # Thư viện adapter chia sẻ (nếu có)
├── templates/         # Template Django (admin/backoffice)
├── staticfiles/       # Static assets build sẵn
├── manage.py
└── requirement.txt
```

---

## 4. Quy ước cấu trúc một module (chuẩn)
```text
module_name/
├── domain/              # Business thuần, không phụ thuộc framework
│   ├── entities.py
│   ├── value_objects.py
│   └── exceptions.py
├── repositories/
│   ├── interfaces.py   # Interface trừu tượng
│   └── implementations.py
├── infrastructure/
│   ├── django_models.py
│   ├── django_admin.py
│   └── adapters.py      # Tích hợp external service (nếu có)
├── services/
│   └── use_cases.py     # Logic ứng dụng của module (không biết HTTP)
├── api/
│   ├── serializers.py
│   ├── views.py         # Layer mỏng: validate → gọi application/module use case
│   └── urls.py
├── tests/
│   ├── test_domain.py
│   ├── test_services.py
│   └── test_api.py
├── apps.py
└── migrations/
```

**Nguyên tắc:**
- Không để business logic trong `django_models.py` hay `views.py`; tất cả nằm ở `services/use_cases.py` hoặc domain.
- `api/views.py` chỉ làm 3 việc: validate input (serializer) → gọi application use case (hoặc module use case nếu không cần điều phối) → map response theo chuẩn `{success, data}`.
- `domain` tuyệt đối không import Django/DRF/requests.
- `services` trả về domain entity hoặc DTO riêng, **không** trả thẳng ORM model.
- `repositories/implementations.py` là nơi duy nhất truy cập ORM.


## 4.1 Chuẩn hoá URL & namespacing API theo module

- Mọi endpoint của module đặt dưới tiền tố `/api/<module>/`.
- Mỗi `infrastructure/urls.py` cần `app_name` để namespacing rõ ràng.
- `config/urls.py` include từng module theo prefix cố định.

Ví dụ (module catalog):

```python
# services/catalog/infrastructure/urls.py
app_name = "catalog_api"

from django.urls import path
from . import api_views

urlpatterns = [
    path('products/', api_views.list_products_view, name='products_list'),
    # thêm các endpoint khác...
]
```

```python
# config/urls.py
from django.urls import path, include

urlpatterns = [
    path('api/catalog/', include(('services.catalog.infrastructure.urls', 'catalog_api'))),
    # thêm các module khác...
]
```

### API Endpoints hiện có:

#### Identity Module (Authentication)
- `POST /api/identity/signup/` - Đăng ký tài khoản mới
- `POST /api/identity/login/` - Đăng nhập
- `POST /api/identity/logout/` - Đăng xuất
- `GET /api/identity/check-auth/` - Kiểm tra trạng thái đăng nhập
- `POST /api/identity/change-password/` - Đổi mật khẩu

#### Accounts Module (Profile Management)
- `GET /api/accounts/profile/` - Lấy thông tin profile
- `POST /api/accounts/profile/update/` - Cập nhật profile
- `GET /api/accounts/preferences/` - Lấy preferences (theme, language, etc.)
- `POST /api/accounts/preferences/update/` - Cập nhật preferences

**Chi tiết:** Xem [API_DOCUMENTATION.md](API_DOCUMENTATION.md) để biết chi tiết về request/response format và cách tích hợp với React frontend.
---

## 5. Nguyên tắc phụ thuộc (RẤT QUAN TRỌNG)

```
domain
    ↑
repositories
    ↑
infrastructure
    ↑
services
    ↑
application
    ↑
api / interfaces
```

- `domain`        ← thuần business, **không import gì khác**.
- `repositories`  ← import domain để định nghĩa interface và mapping entity.
- `infrastructure`← hiện thực repository/adapters, có thể import domain + repository.
- `services`      ← chứa use case của module, import domain + repository (implementation injected qua constructor).
- `application`   ← import **chỉ** services/use_cases của module (không đụng ORM / infrastructure trực tiếp).
- `api/interfaces`← import application use case (mặc định). Chỉ được gọi thẳng module service nếu workflow hoàn toàn nằm trong 1 module và được chấp thuận.

**❌ Cấm:**
- Domain import Django
- Service import request / response
- Service gọi trực tiếp ORM
- Module import ngược lên `application`

---

## 6. Vai trò các tầng

- **Domain:** Ngôn ngữ nghiệp vụ, Entity, Value Object, Exception, không biết DB/HTTP.
- **Repositories:** Định nghĩa + hiện thực truy cập dữ liệu, mapping domain ↔ ORM.
- **Infrastructure:** ORM model, adapter external service, admin; không để business ở đây.
- **Services (module):** Use case nội bộ module. Nhận DTO/domain input, gọi repository, trả domain object hoặc DTO.
- **Application:** Ghép nhiều module services thành workflow. Quản lý transaction, retry, event nội bộ.
- **API/Interfaces:** Adapter (HTTP, CLI, task) validate payload, gọi application use case, format `{success, data}` response.

---

## 7. Tenant – xương sống của SaaS

Tenant chịu trách nhiệm:
- Xác định dữ liệu thuộc về ai
- Gắn subscription, quota
- Resolve tenant từ request

**Luồng request chuẩn:**
```text
HTTP Request
 ↓
TenantMiddleware
 ↓
resolve tenant
 ↓
request.tenant
 ↓
Service logic
```

---

## 8. Cách thêm module mới (ví dụ: analytics)

**Bước 1:** Tạo module  
`mkdir services/analytics`

**Bước 2:** Áp dụng cấu trúc chuẩn
```text
analytics/
├── domain/
├── repositories/
├── infrastructure/
├── services/
├── api/
├── tests/
└── apps.py
```

**Bước 3:** Nguyên tắc tích hợp
- Khai báo module trong `INSTALLED_APPS` (SHARED_APPS hay TENANT_APPS tuỳ use case).
- Tạo `infrastructure/django_admin.py` và import trong `apps.py.ready()` để Auto register admin.
- Viết use case trong `services/use_cases.py`; expose function/class rõ ràng để application layer gọi được.
- `api/views.py` của module chỉ chứa endpoint nội bộ nếu thật sự cần. Endpoint phục vụ frontend phải đi qua application.
- Không import module khác trực tiếp. Giao tiếp qua application hoặc interface/DTO được định nghĩa chung.
- Service luôn nhận `tenant`, `actor` và dữ liệu thuần (dict/value object). Không nhận request hoặc model thô.

**Bước 4:** Kết nối với application
- Tạo file tương ứng trong `application/use_cases/<module>/` hoặc `application/orchestrators/`.
- Map module service vào application use case (dependency inject qua constructor hoặc provider).
- Cập nhật adapter HTTP tại `application/interfaces` (hoặc refactor DRF view hiện có) để gọi use case mới.
- Viết tài liệu ngắn mô tả luồng mới trong `application/README.md` (nếu ảnh hưởng cross-module).

---
## 8.1 Nguyên tắc mới: Module tự đăng ký Admin

    Để hệ thống quản trị (admin) hoạt động như một core test & back-office, mỗi module cần tuân theo các nguyên tắc sau:

**Nguyên tắc:**
1. Module tự expose khả năng quản trị
    - Thông qua file infrastructure/django_admin.py
    - Sử dụng Django Admin mặc định
2. Core admin KHÔNG import module cụ thể
    - Core admin chỉ cung cấp base class / policy chung
    - Không phụ thuộc business module
    - Admin KHÔNG gọi ORM trực tiếp cho nghiệp vụ
3. Admin đóng vai trò adapter
    - Gọi vào Service layer của module
    - Luồng chuẩn
        Django Admin UI
        ↓
        Module admin adapter
        ↓
        Service layer
        ↓
        Repository
        ↓
        Database
**Lợi ích**
- Tạo module mới → admin dùng được ngay
- Không phá kiến trúc khi scale
- Admin trở thành công cụ test kiến trúc sống


## 8.2 Cơ chế truy cập dữ liệu (Data Access Pattern)

Có **2 entry point** cho dữ liệu:

### A. API Endpoint (React Frontend chính)
```
HTTP Request → module/api/views.py → application.use_case → module.service → repository → DB
```
- Trả JSON
- Dùng cho React SPA
- Có thể dùng cho mobile app sau
- ✅ Bắt buộc đi qua application.use_case nếu use-case chạm >1 module (plan ↔ quota ↔ billing, signup tạo tenant,...)

### B. Django Admin (Back-office & Testing)
```
Django Admin UI → infrastructure/django_admin.py → Service → Repository → DB
```
- Trả HTML
- Dùng cho admin quản lý
- **Cấm** gọi ORM trực tiếp

### ⚠️ Nguyên tắc:
- **Cả 2 đều phải gọi qua Service layer**
- **Không có "shortcut" trực tiếp ORM**
- Nếu thay đổi logic → thay 1 chỗ (Service)
- Both Admin & API đều được cập nhật

### Diagram:
```
Django Admin ──┐
               ├→ Service → Repository → DB
React API ────┘

(Service là SINGLE SOURCE OF TRUTH)
```

## 8.3 Frontend độc lập cùng domain

- Frontend (React SPA) gọi relative path `/api/...` → không cần CORS nếu cùng domain.
- Nếu chạy khác domain → cấu hình CORS ở settings và dùng base URL trong frontend.

---

## 8.4 Nguyên tắc Models và Multi-tenancy

### Schema-per-Tenant Strategy

Hệ thống sử dụng **django-tenants** với chiến lược **Schema-per-Tenant**:

- **Public schema**: Chứa dữ liệu chung (Tenant, User, Domain mapping)
- **Tenant schema**: Mỗi tenant có riêng PostgreSQL schema (tenant_xxx)
- **Tự động routing**: django-tenants tự động switch schema context

### Phân loại Models

#### 1. SHARED_APPS Models (Public Schema)
Chỉ các model **Core Platform** nằm ở public schema:
```python
SHARED_APPS = [
    'django_tenants',  # PHẢI đứng đầu
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.admin',
    
    # Core platform modules
    'core.tenants',      # Tenant, TenantDomain
    'core.identity',     # Authentication
    'core.accounts',     # User profiles
]
```

**❗ Quy tắc SHARED_APPS:**
- Chỉ chứa model quản lý platform (tenant, user, auth)
- **KHÔNG BAO GIỜ** thêm business model vào đây
- Model ở đây truy cập được từ mọi schema

#### 2. TENANT_APPS Models (Tenant Schema)
Tất cả **Business Models** nằm ở tenant schema:
```python
TENANT_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    
    # Core tenant-specific
    'core.access',       # RBAC: Membership, Role, Permission
    
    # Business services (Phân tách dữ liệu theo tenant)
    'services.products', # Product, PriceHistory
    'services.catalog',  # Category, Brand
    'services.analytics',# Report, Metric
]
```

**❗ Quy tắc TENANT_APPS:**
- Mọi business logic phải ở đây
- Dữ liệu tự động isolated theo tenant
- Mỗi tenant thấy RIÊNG dữ liệu của mình

### Tương tác giữa Shared và Tenant Models

```python
# ✅ ĐÚNG: Tenant schema tham chiếu đến shared
class Membership(models.Model):  # Trong TENANT_APPS
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # OK: User ở SHARED
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # OK

# ❌ SAI: Shared KHÔNG được tham chiếu Tenant model
class User(models.Model):  # Trong SHARED_APPS
    favorite_product = models.ForeignKey(Product)  # SAI! Product ở TENANT_APPS
```

**Nguyên tắc:**
- ✅ Tenant → Shared: OK (via ForeignKey)
- ❌ Shared → Tenant: CẤM (sẽ lỗi migration)

---

## 8.5 Hướng dẫn triển khai Service Module mới

### Template chuẩn cho Service Module

Khi tạo module business mới (ví dụ: `services/orders`), tuân thủ template:

```text
services/orders/
├── __init__.py
├── apps.py                    # Django AppConfig
├── domain/                    # Pure business logic
│   ├── __init__.py
│   ├── entities.py           # Order, OrderItem, OrderStatus
│   └── exceptions.py         # OrderNotFoundError, InvalidOrderError
├── services/                  # Use-case orchestration
│   ├── __init__.py
│   └── order_service.py      # create_order(), cancel_order()
├── repositories/              # Data access interface
│   ├── __init__.py
│   └── order_repo.py         # OrderRepository (ABC)
├── infrastructure/            # Django implementation
│   ├── __init__.py
│   ├── django_models.py      # OrderModel, OrderItemModel
│   ├── django_repository.py  # DjangoOrderRepository
│   ├── api_views.py          # JSON endpoints
│   └── django_admin.py       # Admin adapter
├── migrations/
│   └── __init__.py
└── tests/
    └── test_order_service.py
```

### Checklist triển khai module mới

#### Bước 1: Domain Layer
```python
# domain/entities.py
from dataclasses import dataclass
from enum import Enum
from uuid import UUID
from datetime import datetime

class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

@dataclass
class Order:
    id: UUID
    tenant_id: UUID  # ❗ BẮT BUỘC: Mọi entity phải có tenant_id
    customer_id: UUID
    status: OrderStatus
    total_amount: float
    created_at: datetime
```

#### Bước 2: Repository Interface
```python
# repositories/order_repo.py
from abc import ABC, abstractmethod
from uuid import UUID

class OrderRepository(ABC):
    @abstractmethod
    async def create(self, order: Order) -> Order:
        pass
    
    @abstractmethod
    async def get_by_id(self, order_id: UUID, tenant_id: UUID) -> Optional[Order]:
        # ❗ Luôn nhận tenant_id để đảm bảo isolation
        pass
```

#### Bước 3: Service Layer
```python
# services/order_service.py
class OrderService:
    def __init__(self, repository: OrderRepository):
        self.repository = repository
    
    async def create_order(
        self,
        tenant_id: UUID,  # ❗ BẮT BUỘC: Service luôn nhận tenant_id
        customer_id: UUID,
        items: List[OrderItem],
    ) -> Order:
        # Business logic here
        order = Order.create(tenant_id=tenant_id, ...)
        return await self.repository.create(order)
```

#### Bước 4: Django Models (Tenant Schema)
```python
# infrastructure/django_models.py
from django.db import models
from django_tenants.models import TenantMixin  # ❌ KHÔNG dùng - chỉ cho Tenant model

class OrderModel(models.Model):
    """
    ❗ Model này TỰ ĐỘNG nằm trong tenant schema
    Không cần inherit TenantMixin
    """
    id = models.UUIDField(primary_key=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'orders'  # Nằm trong tenant schema
        indexes = [
            models.Index(fields=['customer', 'created_at']),
        ]
```

#### Bước 5: API Views (JSON Endpoints)
```python
# infrastructure/api_views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync

@csrf_exempt
@require_http_methods(["POST"])
def create_order_view(request):
    """POST /api/orders/ → Tạo đơn hàng mới"""
    try:
        data = json.loads(request.body)
        
        # ❗ Lấy tenant từ request (set bởi middleware)
        tenant_id = request.tenant.id
        
        service = _get_order_service()
        order = async_to_sync(service.create_order)(
            tenant_id=tenant_id,
            customer_id=data['customer_id'],
            items=data['items']
        )
        
        return JsonResponse({
            'success': True,
            'order': _order_to_dict(order)
        }, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

#### Bước 6: URLs
```python
# infrastructure/urls.py (hoặc urls.py ở root module)
from django.urls import path
from .infrastructure import api_views

app_name = 'orders'

urlpatterns = [
    path('', api_views.list_orders_view, name='list'),
    path('', api_views.create_order_view, name='create'),
    path('<uuid:order_id>/', api_views.get_order_view, name='get'),
]
```

#### Bước 7: Đăng ký module
```python
# config/settings.py
TENANT_APPS = [
    # ...existing apps
    'services.orders',  # ❗ Thêm vào TENANT_APPS (KHÔNG phải SHARED_APPS)
]

# config/urls.py
urlpatterns = [
    # ...
    path('api/orders/', include('services.orders.urls')),
]
```

---

## 9. ⚠️ NGUYÊN TẮC CỐT LÕI - TUYỆT ĐỐI TUÂN THỦ

### 9.1 Cấm Phá Vỡ Cấu Trúc Module

**❌ TUYỆT ĐỐI CẤM:**

1. **Thay đổi cấu trúc thư mục chuẩn**
   ```
   ❌ services/orders/models.py          # SAI: Không dùng tên file cũ
   ❌ services/orders/views.py            # SAI: Phải là api_views.py
   ❌ services/orders/business/           # SAI: Phải là services/
   ```

2. **Bỏ qua các layer bắt buộc**
   ```python
   ❌ API View → Django ORM trực tiếp    # SAI: Phải qua Service
   ❌ Admin → Django ORM trực tiếp       # SAI: Phải qua Service
   ❌ Service → Django Model trực tiếp   # SAI: Phải qua Repository
   ```

3. **Import ngược chiều**
   ```python
   ❌ domain/entities.py import Django   # SAI: Domain phải pure
   ❌ services/ import request/response  # SAI: Service không biết HTTP
   ❌ SHARED_APPS import TENANT_APPS     # SAI: Sẽ lỗi migration
   ```

4. **Thay đổi SHARED_APPS tuỳ tiện**
   ```python
   ❌ SHARED_APPS += ['services.products']  # SAI: Business model phải ở TENANT
   ❌ Xoá 'core.tenants' khỏi SHARED_APPS   # SAI: Core không được động
   ```

### 9.2 Nguyên Tắc Sửa Đổi Cấu Hình

**Khi cần thay đổi settings.py:**

✅ **ĐƯỢC PHÉP:**
- Thêm module mới vào `TENANT_APPS`
- Thêm middleware (sau khi review)
- Thêm CORS domain mới
- Cập nhật environment variables

❌ **CẤM:**
- Sửa thứ tự `SHARED_APPS` (django_tenants phải đầu)
- Xoá `DATABASE_ROUTERS`
- Thay đổi `TENANT_MODEL` hoặc `TENANT_DOMAIN_MODEL`
- Tắt middleware `TenantMiddleware`

**Quy trình an toàn:**
1. Backup `config/settings.py`
2. Chỉ thay đổi 1 section tại 1 thời điểm
3. Chạy `python manage.py check` sau mỗi thay đổi
4. Test migration: `python manage.py migrate_schemas --shared`
5. Commit ngay nếu thành công

### 9.3 Code Review Checklist

Trước khi merge code module mới:

- [ ] Domain entities không import Django
- [ ] Service không biết HttpRequest/JsonResponse
- [ ] Repository là interface thuần (ABC)
- [ ] Model nằm trong `TENANT_APPS` (nếu business logic)
- [ ] API views gọi qua service layer
- [ ] Admin adapter gọi qua service layer
- [ ] Có `tenant_id` trong mọi entity/query
- [ ] URL có `app_name` cho namespacing
- [ ] Migrations chạy thành công
- [ ] Django check không có lỗi

### 9.4 Recovery từ Vi Phạm

Nếu đã vi phạm nguyên tắc:

```bash
# 1. Rollback migrations nếu có
python manage.py migrate services.orders zero

# 2. Checkout lại code sạch
git checkout HEAD~1 config/settings.py

# 3. Xoá cache Python
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete

# 4. Restart services
pkill -f gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8005

# 5. Verify
python manage.py check
curl http://localhost:8005/api/tenants/
```

---

## 10. Nguyên tắc mở rộng lâu dài

- Có thể tách module thành microservice
- Có thể thay ORM / DB
- Có thể dùng Celery / worker độc lập

---

## 11. Checklist kiểm tra kiến trúc

- ✔ Service không biết Django
- ✔ Domain không biết DB
- ✔ Tenant luôn được resolve sớm
- ✔ Có thể test service không cần Django
- ✔ Business models nằm trong TENANT_APPS
- ✔ Mọi entity có `tenant_id`
- ✔ API views và Admin đều qua Service layer
- ✔ Không vi phạm import ngược chiều

---

## 12. Tích Hợp với Core Modules

### 12.1 Tương tác với Tenants Module

Mọi service module phải tương tác với tenant:

```python
# ✅ ĐÚNG: Luôn filter theo tenant
async def get_products(tenant_id: UUID) -> List[Product]:
    return await product_repo.list_by_tenant(tenant_id)

# ❌ SAI: Query không filter tenant
async def get_all_products() -> List[Product]:
    return await product_repo.list_all()  # Leak data!
```

### 12.2 Tương tác với Access Module (RBAC)

Check permission trước khi thực hiện action:

```python
# infrastructure/api_views.py
@require_permission('write:products')
async def create_product_view(request):
    # Middleware đã check permission
    tenant_id = request.tenant.id
    user_id = request.user.id
    
    # Business logic
    service = _get_product_service()
    product = await service.create_product(
        tenant_id=tenant_id,
        created_by=user_id,
        data=request.data
    )
    return JsonResponse({'product': product})
```

### 12.3 Schema Context

Django-tenants tự động set schema context, nhưng cần hiểu:

```python
# Trong tenant schema (tự động)
Product.objects.all()  # Chỉ lấy products của tenant hiện tại

# Force public schema (nếu cần)
from django_tenants.utils import schema_context
with schema_context('public'):
    Tenant.objects.all()  # Lấy tất cả tenants
```

**❗ Chú ý:**
- KHÔNG tự switch schema trong business logic
- Middleware đã handle schema routing
- Chỉ service layer cần biết về tenant_id

---

## 13. Best Practices & Patterns

### 13.1 Service Factory Pattern

```python
# infrastructure/api_views.py
def _get_product_service() -> ProductService:
    """Factory để inject dependencies"""
    repo = DjangoProductRepository()
    return ProductService(repository=repo)

# Lợi ích: Dễ mock khi test, dễ swap implementation
```

### 13.2 Error Handling Pattern

```python
# domain/exceptions.py
class ProductNotFoundError(Exception):
    def __init__(self, product_id: str):
        self.product_id = product_id
        super().__init__(f"Product {product_id} not found")

# infrastructure/api_views.py
@csrf_exempt
def get_product_view(request, product_id):
    try:
        service = _get_product_service()
        product = async_to_sync(service.get_product)(
            product_id=UUID(product_id),
            tenant_id=request.tenant.id
        )
        return JsonResponse({'success': True, 'product': product})
    
    except ProductNotFoundError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=404)
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)
```

### 13.3 Async Repository Pattern

```python
# infrastructure/django_repository.py
from asgiref.sync import sync_to_async

class DjangoProductRepository(ProductRepository):
    async def create(self, product: Product) -> Product:
        @sync_to_async
        def _create():
            db_product = ProductModel(
                id=product.id,
                name=product.name,
                # ... map fields
            )
            db_product.save()
            return self._to_domain(db_product)
        
        return await _create()
```

### 13.4 DTO Conversion Pattern

```python
def _to_domain(self, db_model: ProductModel) -> Product:
    """Convert Django Model → Domain Entity"""
    return Product(
        id=db_model.id,
        name=db_model.name,
        tenant_id=db_model.tenant_id,
        created_at=db_model.created_at,
    )

def _to_dto(self, product: Product) -> dict:
    """Convert Domain Entity → JSON dict"""
    return {
        'id': str(product.id),
        'name': product.name,
        'created_at': product.created_at.isoformat(),
    }
```

---

## 14. Testing Strategy

### 14.1 Service Layer Tests (Pure Python)

```python
# tests/test_product_service.py
import pytest
from uuid import uuid4
from services.products.services.product_service import ProductService
from services.products.repositories.product_repo import ProductRepository

class MockProductRepository(ProductRepository):
    def __init__(self):
        self.products = {}
    
    async def create(self, product):
        self.products[product.id] = product
        return product

@pytest.mark.asyncio
async def test_create_product():
    # Arrange
    repo = MockProductRepository()
    service = ProductService(repository=repo)
    tenant_id = uuid4()
    
    # Act
    product = await service.create_product(
        tenant_id=tenant_id,
        name="Test Product",
        price=100.0
    )
    
    # Assert
    assert product.name == "Test Product"
    assert product.tenant_id == tenant_id
    assert product.id in repo.products
```

### 14.2 API Integration Tests

```python
# tests/test_api.py
from django.test import TestCase, Client
import json

class ProductAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.tenant = create_test_tenant()
    
    def test_create_product(self):
        response = self.client.post(
            '/api/products/',
            data=json.dumps({
                'name': 'Test Product',
                'price': 100.0
            }),
            content_type='application/json',
            HTTP_HOST=self.tenant.domain
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['product']['name'], 'Test Product')
```

---

## 15. Kết luận

Kiến trúc này:
- Không phức tạp hoá sớm
- Phù hợp SaaS thực tế
- Giữ code sạch khi scale

**Rule of thumb:**  
"Code cho SaaS như bạn sẽ bán cho người khác đọc lại sau 2 năm."