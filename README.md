# PriceSynC Backend Architecture

PriceSynC là một nền tảng SaaS đa-tenant được xây dựng xung quanh một kiến trúc phân lớp nghiêm ngặt. Tất cả các luồng chạy được điều phối từ lớp application, trong khi các khả năng kinh doanh được gói gọn bên trong các mô-đun. **API HTTP không còn nằm trong các gói mô-đun mà được expose độc quyền qua các adapter giao diện ứng dụng**.

---

## 1. Bố Cục Thư Mục

```
Saas_app/
├── application/                # Điều phối đa-mô-đun, DTO, adapter giao diện, toggle
│   ├── dto/                    # DTO ứng dụng (command, result, context)
│   ├── use_cases/              # Hành động đơn lẻ (signup, create_tenant, ...)
│   ├── orchestrators/          # Luồng nhiều bước (provisioning, ...)
│   ├── flow_rules/             # Toggle Boolean cho từng bước luồng
│   └── interfaces/             # Adapter giao diện (HTTP, CLI, Celery, webhook)
├── config/                     # Cấu hình Django project
├── core/                       # Mô-đun nền tảng (identity, tenants, billing, ...)
├── services/                   # Mô-đun nghiệp vụ tùy chọn (products, crawl, ...)
├── interfaces/                 # Adapter chia sẻ (email, integration)
├── templates/                  # Override template Django
├── staticfiles/                # Tài sản tĩnh đã thu thập
├── manage.py
└── requirement.txt
```

**Thay đổi chính:**
- `core.<module>.api` đã không dùng nữa. API mới nằm dưới `application/interfaces/<type>/<flow>/`.
- Mô-đun giữ cấu trúc phân lớp nhưng **KHÔNG có thư mục api**.

---

## 2. Lớp Application (Lớp Điều Phối Trung Tâm)

Lớp application là điểm vào duy nhất cho mọi quy trình chạy. Nó:
- Ghép nối các bước liên quan đến nhiều mô-đun.
- Áp dụng chính sách nền tảng trước khi gọi module service.
- Xác định DTO ổn định cho giao diện.
- Cho phép admin bật/tắt bước mà không cần sửa code (toggle).

### 2.1 Cấu Trúc Chi Tiết

#### a. **application/dto/** – Hợp Đồng Dữ Liệu
Định nghĩa các command (đầu vào) và result (kết quả) được sử dụng across orchestrators:
- `SignupCommand`, `ProvisioningContext`: DTO lệnh
- `SignupResult`, `CreateTenantResult`: DTO kết quả
- Quy tắc: DTO ứng dụng **không bao giờ chứa logic domain** và **không được mô-đun dùng**

#### b. **application/use_cases/** – Hành Động Đơn Lẻ
Mỗi file định nghĩa một hành động kinh doanh nhỏ:
- Ví dụ: `SignupUseCase`, `CreateTenantUseCase`, `AssignPlanUseCase`
- Mô tả: Nhận DTO command → gọi 1–2 mô-đun service via provider → trả DTO result
- **Không quản lý context dài**: Orchestrator xử lý ghép nối

#### c. **application/orchestrators/** – Luồng Nhiều Bước
Ghép nhiều use case thành sequence cố định:
- Ví dụ: `ProvisioningFlowOrchestrator` (signup → verify → signin → tenant → ... → activate)
- Mô tả: Nhận command ban đầu → thực thi từng use case → cập nhật context → trả context cuối
- **Tôn trọng toggle**: Trước mỗi bước, kiểm tra toggle; nếu disable → bỏ qua bước nhưng giữ context

#### d. **application/flow_rules/** – Toggle Cấu Hình
Lưu trữ Boolean toggle cho từng bước luồng (flow_code + step_code → is_enabled):
- Django Admin: Admin có thể bật/tắt bước
- **Lưu ý**: Đây là **infrastructure**, application chỉ **đọc** để biết có thực thi bước hay không
- **Không ảnh hưởng logic**: Nếu toggle = false, bước bị bỏ qua nhưng context vẫn chuyển tiếp

#### e. **application/interfaces/** – Adapter Giao Diện
Chứa các adapter để dịch input external sang DTO ứng dụng:
- `interfaces/http/`: DRF adapter cho HTTP
- `interfaces/cli/`: Adapter CLI
- `interfaces/celery/`: Adapter Celery task
- `interfaces/webhook/`: Adapter webhook
- Mỗi adapter: Hiểu input của nó → dịch sang DTO → gọi use case/orchestrator → định dạng output

### 2.2 Quy Tắc Phụ Thuộc (Một Chiều Chặt)

```
Module domain (kinh doanh thuần)
  ↑
Module repositories (trừu tượng)
  ↑
Module infrastructure (ORM, admin)
  ↑
Module services (use_cases + providers)
  ↑
Application (use_cases + orchestrators + flow_rules)
  ↑
Application/interfaces (adapter HTTP, CLI, Celery, webhook)
```

**Cấm tuyệt đối:**
- ❌ Module **KHÔNG BAO GIỜ** import `application`
- ❌ Application **không truy cập ORM trực tiếp** (chỉ gọi module service via provider)
- ❌ Domain **không import Django/DRF**
- ❌ Services **không trả ORM model** (trả domain entity hoặc DTO)
- ❌ Giao diện **không chứa logic kinh doanh** (chỉ dịch input → DTO)

**Hệ quả:**
- Thay đổi application logic → không ảnh hưởng mô-đun
- Thêm giao diện mới (CLI, webhook) → không ảnh hưởng mô-đun hoặc application
- Vi phạm quy tắc → **lỗi kiến trúc** cần sửa ngay

---

## 3. Luồng Onboarding và Toggle Cấu Hình

Luồng onboarding là xương sống cố định:

```
Đăng ký → Xác thực Email → Đăng nhập → Tạo Tenant → Giải quyết Subscription 
→ Chọn Plan → Báo giá/Thanh toán → Kích hoạt Tenant
```

- Mỗi bước là một use case hoặc hành động nhỏ
- Mỗi bước được ánh xạ đến một toggle Boolean trong `application/flow_rules`
- **Admin công cụ**: Django admin tại **Application Flow Toggles** cho phép bật/tắt từng bước
- **Quy trình**: Orchestrator đọc toggle trước khi gọi handler; nếu disable → bỏ qua nhưng context vẫn chuyển tiếp
- **Wiring**: Handler được tiêm via provider của từng mô-đun (identity, tenants, subscription, billing, notification)

Mẫu này sẽ được tái sử dụng cho các luồng khác (khôi phục churn, quy trình tùy chỉnh) khi cần.

---

## 4. Cấu Trúc Mô-đun (Core & Services)

Mô-đun giữ thiết kế phân lớp nhưng **không có thư mục api**:

```
module_name/
├── domain/
│   ├── entities.py           # Thực thể, giá trị, ngoại lệ kinh doanh
│   ├── value_objects.py
│   └── exceptions.py
├── repositories/
│   ├── interfaces.py         # Giao diện trừu tượng truy cập dữ liệu
│   └── implementations.py    # Hiện thực ORM
├── infrastructure/
│   ├── django_models.py      # ORM models
│   ├── django_admin.py       # ⭐ Admin adapter (backoffice cho system admin)
│   └── adapters.py           # Tích hợp dịch vụ bên ngoài (nếu có)
├── services/
│   ├── use_cases.py          # Logic ứng dụng mô-đun
│   └── providers.py          # Factory xây dựng use case với repository được tiêm
├── dto/                      # (tuỳ chọn) DTO nội bộ mô-đun
│   └── contracts.py
├── tests/
├── apps.py
└── migrations/
```

**Nguyên tắc:**
- Logic kinh doanh sống trong `domain` và `services`; infrastructure được giữ nhỏ
- `services/providers.py` là hợp đồng của mô-đun với application layer
- **Mô-đun KHÔNG BAO GIỜ import từ `application` hoặc mô-đun khác** — ghép nối xảy ra ở application
- `infrastructure/django_admin.py`: Admin adapter cho backoffice, **bắt buộc gọi service**
- File được tải tự động qua `apps.py.ready()` và đăng ký với `core.admin_core.CustomAdminSite`
- Mô-đun có thể định nghĩa DTO nội bộ riêng (không chia sẻ với application)

**Chi tiết về `django_admin.py`**:
- **Vai trò**: Adapter cho giao diện backoffice (Django Admin UI)
- **Người dùng**: System admin (không phải khách hàng)
- **Nguyên tắc**: Admin class chỉ làm adapter, **mọi logic nghiệp vụ gọi qua service**
- **Ví dụ**:
  ```python
  @admin.register(MyModel, site=default_admin_site)
  class MyModelAdmin(admin.ModelAdmin):
      def save_model(self, request, obj, form, change):
          service = get_my_service()
          service.update_entity(obj.id, form.cleaned_data)  # ✅ Gọi service
  ```

---

## 5. Giao Diện HTTP và Các Adapter

Vì API tập trung ở application, mỗi adapter tuân theo cùng mẫu:

```
Input (JSON) → Serializer.validate() → DTO → Use case/Orchestrator → Output (JSON)
```

### 5.1 Cấu Trúc Adapter
```
application/interfaces/http/
├── provisioning/
│   ├── serializers.py      # SignupSerializer → SignupCommand
│   ├── views.py            # Gọi ProvisioningFlowOrchestrator
│   └── urls.py             # Đăng ký endpoint
├── billing/
│   ├── serializers.py      # PaymentSerializer
│   ├── views.py            # Gọi PaymentOrchestrator
│   └── urls.py
```

### 5.2 Phản Hồi Tiêu Chuẩn
```json
{
  "success": true,
  "data": {...},
  "error": null,
  "message": ""
}
```

### 5.3 Ưu Điểm
- **Tái sử dụng logic**: Cùng orchestrator được gọi từ HTTP, CLI, Celery, webhook
- **Độc lập giao diện**: Thêm giao diện mới mà không ảnh hưởng orchestrator
- **Kiểm thử dễ**: Kiểm thử orchestrator độc lập với HTTP

---

## 6. Hai Luồng Truy Cập Hệ Thống

### 6.1 Luồng Backoffice (Django Admin) – Quản Trị Viên Hệ Thống

**Mục đích**: Giao diện quản trị nội bộ cho system admin, **hoàn toàn tách biệt** với khách hàng.

**Đặc điểm**:
- URL: `/admin/` (được bảo vệ bởi hash token)
- Giao diện: Django Admin UI (HTML templates)
- Người dùng: System admin, DevOps, support team
- Phạm vi: Quản lý dữ liệu nền tảng, cấu hình hệ thống, toggle luồng, xem audit log

**Kiến trúc**:
```
Django Admin UI → Module django_admin.py (adapter) → Module Service → Repository → DB
```

**Core Module: `core/admin_core/`**
- Cung cấp `CustomAdminSite` với hash-based authentication
- Quản lý admin security middleware
- Tự động load admin configurations từ các module
- Inject AdminService vào middleware và admin site

**Module Admin Adapter (`infrastructure/django_admin.py`)**:

Mỗi module đăng ký admin class tại `infrastructure/django_admin.py`:

```python
# Example: core/tenants/infrastructure/django_admin.py
from django.contrib import admin
from core.admin_core.infrastructure.custom_admin import default_admin_site
from ..services.providers import get_tenant_service

@admin.register(TenantModel, site=default_admin_site)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('schema_name', 'name', 'created_at', 'is_active')
    
    def save_model(self, request, obj, form, change):
        # ✅ ĐÚNG: Gọi service thay vì lưu trực tiếp
        service = get_tenant_service()
        if change:
            service.update_tenant(obj.schema_name, form.cleaned_data)
        else:
            service.create_tenant(form.cleaned_data)
```

**Vai trò `django_admin.py`**:
- **Adapter pattern**: Dịch Django admin actions → module service calls
- **Read-only hoặc Service-backed**: Mọi thay đổi dữ liệu phải qua service layer
- **Audit trail**: Admin có thể xem log, history, metrics
- **Toggle management**: Admin chỉnh flow toggles, rule configs mà không cần deploy

**Quy tắc bắt buộc**:
- ❌ Admin **KHÔNG ĐƯỢC** thao tác ORM trực tiếp (create/update/delete model)
- ✅ Admin **PHẢI** gọi module service cho mọi hành động nghiệp vụ
- ✅ Admin chỉ đọc dữ liệu qua queryset đơn giản, ghi qua service

### 6.2 Luồng Frontend (API) – Khách Hàng

**Mục đích**: Giao diện người dùng cuối (end-user) qua React SPA.

**Đặc điểm**:
- URL: `/api/` (public hoặc authenticated)
- Giao diện: React SPA (consume JSON)
- Người dùng: Khách hàng SaaS, end-users
- Phạm vi: Sử dụng dịch vụ, quản lý dữ liệu nghiệp vụ

**Kiến trúc**:
```
React SPA (fetch JSON) → /api/<flow>/ → application/interfaces/http/
→ Serializer.validate() → DTO → Application use case/orchestrator
→ Module service → Repository → DB
→ JSON response
```

**Ví dụ luồng Signup**:
```
POST /api/provisioning/signup/
  ↓
application/interfaces/http/provisioning/views.py
  ↓ SignupSerializer → SignupCommand (DTO)
  ↓
application/orchestrators/provisioning.py (ProvisioningFlowOrchestrator)
  ↓ gọi identity.signup_service, tenants.create_service, ...
  ↓
JSON: {"success": true, "data": {"user_id": "...", "tenant_id": "..."}}
```

**API Response chuẩn**:
```json
{
  "success": true,
  "data": {...},
  "error": null,
  "message": ""
}
```

### 6.3 So Sánh Hai Luồng

| Khía cạnh | Django Admin (Backoffice) | API (Frontend) |
|---|---|---|
| **Người dùng** | System admin, DevOps | Khách hàng, end-users |
| **Giao diện** | Django Admin HTML | React SPA (JSON) |
| **URL** | `/admin/` | `/api/` |
| **Bảo mật** | Hash token + staff permission | JWT/session + tenant isolation |
| **Mục đích** | Quản trị hệ thống, cấu hình | Sử dụng dịch vụ |
| **Adapter** | `django_admin.py` (admin class) | `application/interfaces/http/` |
| **Service call** | Module service trực tiếp | Application orchestrator → module service |
| **Phạm vi** | Toàn hệ thống (cross-tenant) | Bị giới hạn bởi tenant |

---

## 7. Multi-Tenancy

Nền tảng sử dụng `django-tenants` với cô lập schema-per-tenant:

- **SHARED_APPS**: Public schema (tenants, identity, accounts, `application.flow_rules`)
- **TENANT_APPS**: Tenant schema (mô-đun business; migration chạy per tenant)
- **Middleware**: Giải quyết tenant trước khi API thực thi → mỗi request chạy trong schema đúng

---

## 8. Thêm Luồng Mới

1. Định nghĩa DTO command/result trong `application/dto/`
2. Viết use case hoặc orchestrator dưới `application/use_cases/` hoặc `application/orchestrators/`
3. Dây dẫn module service via provider
4. Tạo adapter giao diện dưới `application/interfaces/<type>/<flow>/`
5. Đăng ký URL và include từ `config/urls.py`
6. Thêm toggle nếu cần điều khiển runtime
7. Viết kiểm thử từ cấp ứng dụng

---

## Tóm Tắt Nguyên Tắc

| Thành phần | Trách nhiệm | Import | Export |
|---|---|---|---|
| **Domain** | Logic kinh doanh thuần | Không gì | Entity, exception |
| **Repository** | Truy cập dữ liệu trừu tượng | Domain | Interface |
| **Infrastructure** | ORM, admin | Domain, repository | ORM model, admin |
| **Module Service** | Use case mô-đun | Domain, repository | Domain entity, DTO |
| **Application** | Ghép nối mô-đun | Module service (provider) | DTO result |
| **Giao diện** | Dịch input → DTO | Application | JSON/output |

**Quy tắc vàng**: Module không bao giờ nhìn thấy Application. Application nhìn thấy mô-đun qua provider. Giao diện nhìn thấy Application. Một chiều, không bao giờ đảo ngược.
