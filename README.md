
# Django SaaS Architecture

## 1. Mục tiêu kiến trúc

- Thiết kế cho SaaS quy mô trung bình
- Backend-first (không phụ thuộc UI)
- Dễ mở rộng module (plug-in style)
- Tách rõ nghiệp vụ – hạ tầng – framework
- Phù hợp Django + các package SaaS hiện có

**Ứng dụng mẫu phục vụ use-case:**
- Lưu product (URL, price, brand, category)
- Theo dõi lịch sử giá theo thời gian
- Giới hạn dịch vụ theo gói (quota URLs / products)

---

## 2. Tư duy cốt lõi

### 2.1 SaaS = Multi-tenant

- Tenant = 1 khách hàng / 1 công ty / 1 account trả phí
- Mọi dữ liệu đều thuộc về tenant
- User chỉ là người dùng bên trong tenant
- ❗ Tenant KHÔNG phải User

---

## 3. Cấu trúc thư mục tổng thể

```text
saas_project/
├── config/            # Django settings & URLs
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   └── urls.py
├── core/          # Core SaaS platform (xương sống)
│   ├── tenants/
│   ├── subscriptions/
│   ├── usage/
│   └── billing/
├── services/          # Business services (custom logic)
│   └── catalog/
├── shared/            # Shared utilities
│   ├── domain/
│   ├── services/
│   └── infrastructure/
├── manage.py
└── requirements.txt
```

---

## 4. Quy ước cấu trúc một module (chuẩn)
```text
module_name/
├── domain/            # Khái niệm nghiệp vụ thuần túy
│   ├── entity.py
│   └── exceptions.py
├── services/          # Logic nghiệp vụ / use-case
│   └── xxx_service.py
├── repositories/      # Interface truy cập dữ liệu
│   └── xxx_repo.py
├── infrastructure/    # Django / ORM / HTTP
│   ├── django_models.py
│   ├── api_views.py          # ← JSON endpoints (for React SPA)
│   ├── urls.py               # ← API routes
│   ├── django_admin.py       # ← Admin adapter
│   └── middleware.py         # ← Optional
├── apps.py
└── migrations/
```

**❗ Lưu ý:** 
- Module **KHÔNG có Django template** (dùng React SPA thay thế)
- API view **chỉ trả JSON**, không render HTML
- Nếu cần back-office, dùng Django Admin thông qua service layer


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

- `domain`        ← không import gì
- `repositories`  ← import domain
- `services`      ← import domain + repositories
- `infrastructure`← import services / repositories

**❌ Cấm:**
- Domain import Django
- Service import request / response
- Service gọi trực tiếp ORM

---

## 6. Vai trò các tầng

- **Domain:** Định nghĩa ngôn ngữ nghiệp vụ, Entity, Value Object, Exception, không biết DB, HTTP, Django
- **Services:** Điều phối nghiệp vụ, thực hiện use-case, nhận input thuần (tenant, data)
- **Repositories:** Cổng truy cập dữ liệu, che giấu DB implementation
- **Infrastructure:** Django ORM, API Views, Middleware

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
├── services/
├── repositories/
├── infrastructure/
    └── django_admin.py  # (khuyến nghị) đăng ký Django Admin
└── apps.py
```

**Bước 3:** Nguyên tắc tích hợp
- Module bắt buộc khai báo trong INSTALLED_APPS
- Module tự đăng ký admin (nếu cần quản trị)
- Core admin không chỉnh sửa khi thêm module mới
- Service luôn nhận tenant
- Không truy cập DB trực tiếp
- Không phụ thuộc module khác (trừ qua service)

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
HTTP Request → api_views.py → Service → Repository → DB
```
- Trả JSON
- Dùng cho React SPA
- Có thể dùng cho mobile app sau

### B. Django Admin (Back-office & Testing)
```
Django Admin UI → admin.py (adapter) → Service → Repository → DB
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

## 9. Nguyên tắc mở rộng lâu dài

- Có thể tách module thành microservice
- Có thể thay ORM / DB
- Có thể dùng Celery / worker độc lập

---

## 10. Checklist kiểm tra kiến trúc

- ✔ Service không biết Django
- ✔ Domain không biết DB
- ✔ Tenant luôn được resolve sớm
- ✔ Có thể test service không cần Django

---

## 11. Kết luận

Kiến trúc này:
- Không phức tạp hoá sớm
- Phù hợp SaaS thực tế
- Giữ code sạch khi scale

**Rule of thumb:**  
"Code cho SaaS như bạn sẽ bán cho người khác đọc lại sau 2 năm."