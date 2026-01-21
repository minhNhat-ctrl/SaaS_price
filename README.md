# PriceSynC Backend Architecture

PriceSynC là một nền tảng SaaS đa-tenant được xây dựng xung quanh một kiến trúc phân lớp nghiêm ngặt. Tất cả các luồng chạy được điều phối từ lớp application, trong khi các khả năng kinh doanh được gói gọn bên trong các mô-đun. **API HTTP không còn nằm trong các gói mô-đun mà được expose độc quyền qua các adapter giao diện ứng dụng**.

---

## 1. Bố Cục Thư Mục

```
Saas_app/
├── application/                # Điều phối đa-mô-đun, DTO, flow, adapter giao diện
│   ├── dto/                    # DTO ứng dụng (command, context, result)
│   ├── flows/                  # Flow orchestrator (multi-step sequence)
│   ├── contracts/              # Protocol definitions cho flow handler
│   ├── config/                 # YAML config cho flows (metadata, documentation)
│   ├── services/               # Shared utilities (FlowContext, config loader)
│   ├── api/                    # HTTP API endpoints (DRF views, serializers)
│   └── flow_rules/             # Toggle Boolean cho từng bước luồng (deprecated - use YAML config)
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
- ✅ API endpoint nằm dưới `application/api/<domain>/` (không phải `interfaces/<type>/`)
- ✅ Flow orchestrator nằm dưới `application/flows/<domain>/` (không phải `orchestrators/`)
- ✅ Thêm `application/contracts/` để define Protocol handler
- ✅ Thêm `application/services/` cho shared utilities (FlowContext, loader)
- ✅ Thêm `application/config/` cho YAML metadata flow
- ❌ Mô-đun **KHÔNG có thư mục api** (chỉ giữ domain, repositories, infrastructure, services)
- ⚠️ `flow_rules/` đã deprecated - dùng YAML config thay vào

---

## 2. Lớp Application (Lớp Điều Phối Trung Tâm)

Lớp application là điểm vào duy nhất cho mọi quy trình chạy. Nó:
- Ghép nối các bước liên quan đến nhiều mô-đun (multi-step flow).
- Áp dụng chính sách nền tảng trước khi gọi module service.
- Xác định DTO ổn định (contract) cho HTTP API.
- Cho phép quản lý flow behavior qua YAML config (metadata, documentation).

### 2.1 Cấu Trúc Chi Tiết

#### a. **application/api/** – HTTP API Endpoint (Controller Layer)
Chứa DRF views, serializers, URL router cho HTTP endpoints:
- Vai trò: Nhận request từ client (SPA/Mobile) → validate → gọi flow → format response
- Cấu trúc: `api/<domain>/` (e.g., `api/identity/`, `api/provisioning/`, `api/business/`)
- Mỗi file = một endpoint (e.g., `signup.py`, `signin.py`, `recover_password.py`)
- Quy tắc: Không chứa logic, chỉ validate → flow → JSON response
- Response chuẩn: `{"success": bool, "data": {}, "error": null, "message": str}`

#### b. **application/dto/** – Data Transfer Objects (Contract)
Định nghĩa các command (input), context (state), result (output) được sử dụng in flows:
- `SignupCommand`: Input từ API request
- `SignupContext`: State qua từng bước flow
- `SignupResult`: Output trả về client
- Quy tắc: DTO ứng dụng **không chứa logic domain** và **không được mô-đun dùng trực tiếp**
- Immutable nếu có thể (frozen=True)

#### c. **application/flows/** – Flow Orchestrator (Multi-Step Sequence)
Ghép nhiều module service thành sequence cố định:
- Ví dụ: `signup_flow.py` (3 bước), `tenant_onboarding_flow.py` (8 bước)
- Vai trò: Nhận command ban đầu → thực thi từng bước → cập nhật context → trả context cuối
- Bước nào được skip? Nếu handler không được inject hoặc không cần thiết
- Quy tắc: Không truy cập DB trực tiếp, chỉ gọi module service qua provider hoặc inject

#### d. **application/contracts/** – Protocol/Interface Definitions
Định nghĩa Protocol (typing.Protocol) cho flow handler:
- Ví dụ: `SignupHandlerProtocol`, `EmailHandlerProtocol`, `TenantHandlerProtocol`
- Vai trò: Define contract giữa flow và module service
- Lợi ích: Decouple flow khỏi implementation cụ thể, dễ mock trong test
- Quy tắc: Chỉ định nghĩa method signature, không implement

#### e. **application/config/** – YAML Config (Flow Metadata)
Cấu hình flow dưới dạng YAML (metadata, documentation):
- Ví dụ: `provisioning.yaml`, `identity.yaml`, `billing.yaml`
- Vai trò: Document flow steps, description, owner
- Lợi ích: Dễ đọc, dễ maintain, không ảnh hưởng runtime
- Note: Không phải toggle Boolean (cái đó nằm ở `flow_rules/`)

#### f. **application/services/** – Shared Utilities
Chứa shared utilities cho application layer:
- `flow_context.py`: FlowContext manager (giữ state xuyên suốt flow)
- `config_loader.py`: Load YAML config
- `flow_logger.py`: Flow execution logger
- Quy tắc: Không chứa logic domain, chỉ hỗ trợ flow execution

#### g. **application/flow_rules/** – Toggle Boolean (Deprecated)
Lưu trữ Boolean toggle cho từng bước luồng:
- ⚠️ **Deprecated** - dùng YAML config trong `application/config/` thay vào
- Cách cũ: flow_code + step_code → is_enabled (database model)
- Cách mới: YAML metadata cho documentation, logic trong flow orchestrator

### 2.2 Quy Tắc Phụ Thuộc (Một Chiều Chặt)

```
Module domain (logic kinh doanh thuần)
  ↑
Module repositories (truy cập dữ liệu trừu tượng)
  ↑
Module infrastructure (ORM, admin adapter)
  ↑
Module services (use_cases + providers)
  ↑
Application (flows + api + dto + contracts)
  ↑
Application/api (HTTP endpoint - entry point cho client)
```

**Cấm tuyệt đối:**
- ❌ Module **KHÔNG BAO GIỜ** import `application`
- ❌ Module **KHÔNG CÓ** thư mục `api/` (API endpoint nằm ở `application/api/`)
- ❌ Application **không truy cập ORM trực tiếp** (chỉ gọi module service via provider)
- ❌ Domain **không import Django/DRF**
- ❌ Services **không trả ORM model** (trả domain entity hoặc DTO)
- ❌ HTTP API **không chứa logic kinh doanh** (chỉ validate → flow → response)

**Hệ quả:**
- Thay đổi application logic → không ảnh hưởng mô-đun
- Thêm giao diện mới (CLI, webhook) → không ảnh hưởng mô-đun hoặc application
- Vi phạm quy tắc → **lỗi kiến trúc** cần sửa ngay

---

## 3. Flow Orchestration Pattern

### 3.1 Ví Dụ: Tenant Onboarding Flow

Luồng (flow) là xương sống cố định để orchestrate multiple steps:

```
Signup → Verify Email → Signin → Create Tenant → Resolve Subscription
→ Assign Plan → Quote/Charge → Activate Tenant
```

Mỗi bước là:
- **Input:** DTO command (cho bước đầu) hoặc FlowContext (cho bước tiếp)
- **Process:** Gọi module service (via provider hoặc inject)
- **Output:** Update FlowContext với kết quả
- **Skip logic:** Nếu handler không inject → bước được skip, context vẫn chuyển tiếp

### 3.2 YAML Config vs Toggle

**YAML Config** (`application/config/`):
- Metadata flow: description, steps, owner
- Dùng cho documentation, không affect runtime
- Dễ đọc và maintain

**Toggle Boolean** (`application/flow_rules/`):
- Database model: flow_code + step_code → is_enabled
- Admin có thể bật/tắt từng bước qua Django Admin
- **⚠️ Deprecated** - nên dùng YAML config thay vào
- Quy trình cũ: Orchestrator đọc toggle, nếu disable → bỏ qua bước

### 3.3 Handler Injection Pattern

**Pattern 1: Provider Factory**
```python
from core.identity.services.providers import get_signup_service
service = get_signup_service()  # Get real implementation
```

**Pattern 2: Constructor Injection**
```python
flow = SignupFlow(signup_handler=mock_handler)
```

**Pattern 3: Lazy Loading**
```python
@property
def signup_service(self):
    if self._signup_service is None:
        self._signup_service = get_signup_service()
    return self._signup_service
```

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

## 5. HTTP API Layer Pattern

### 5.1 Kiến Trúc API Endpoint

```
POST /api/identity/signup/ (HTTP Request)
  ↓
application/api/identity/signup.py (APIView)
  ↓ SignupSerializer.validate() → SignupCommand (DTO)
  ↓
application/flows/identity/signup_flow.py (Flow orchestrator)
  ↓ gọi module service (identity, notification, tenant, ...)
  ↓
JSON Response: {"success": true, "data": {...}}
```

### 5.2 Cấu Trúc API Endpoint
```
application/api/
├── identity/
│   ├── signup.py           # POST /api/identity/signup/
│   ├── signin.py           # POST /api/identity/signin/
│   ├── recover_password.py # POST /api/identity/recover-password/
│   └── urls.py
├── provisioning/
│   ├── create_tenant.py    # POST /api/provisioning/tenants/
│   └── urls.py
├── business/
│   ├── create_product.py   # POST /api/business/products/
│   └── urls.py
└── urls.py                 # URL router tổng hợp
```

### 5.3 Mẫu API Endpoint
```python
# application/api/identity/signup.py
class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8)
    
    def to_command(self) -> SignupCommand:
        return SignupCommand(**self.validated_data)

class SignupAPIView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        command = serializer.to_command()
        flow = SignupFlow()  # hoặc get_signup_flow()
        context = flow.execute(command)
        
        return Response({
            "success": True,
            "data": {
                "user_id": context.user_id,
                "email": context.email,
                "requires_verification": context.requires_verification
            },
            "error": None,
            "message": "Signup successful"
        }, status=status.HTTP_201_CREATED)
```

### 5.4 Phản Hồi Tiêu Chuẩn
```json
{
  "success": true,
  "data": {...},
  "error": null,
  "message": "Operation completed successfully"
}
```

### 5.5 Ưu Điểm
- **Tái sử dụng flow**: Cùng flow được gọi từ HTTP, CLI, Celery, webhook
- **Độc lập giao diện**: Thêm giao diện mới mà không ảnh hưởng flow logic
- **Kiểm thử dễ**: Kiểm thử flow với mock handlers độc lập với HTTP layer

---

## 6. Flow Development Workflow

### 6.1 Bước Tạo Flow Mới

**Bước 1:** Định nghĩa DTO
```python
# application/dto/identity.py
@dataclass
class SignupCommand:
    email: str
    password: str
    source: str = "web"

@dataclass
class SignupContext:
    user_id: Optional[str] = None
    verification_token: Optional[str] = None
    requires_verification: bool = False

@dataclass
class SignupResult:
    user_id: str
    requires_verification: bool
```

**Bước 2:** Định nghĩa Contract/Protocol (nếu cần decouple)
```python
# application/contracts/identity.py
class SignupHandlerProtocol(Protocol):
    def check_email_unique(self, email: str) -> bool: ...
    def create_user(self, email: str, password: str) -> User: ...
```

**Bước 3:** Implement Flow Orchestrator
```python
# application/flows/identity/signup_flow.py
@dataclass
class SignupFlow:
    signup_handler: Optional[SignupHandlerProtocol] = None
    
    def execute(self, command: SignupCommand) -> SignupContext:
        service = self.signup_handler or get_signup_service()
        # Step 1, 2, 3...
        return context
```

**Bước 4:** Tạo API Endpoint
```python
# application/api/identity/signup.py
class SignupAPIView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        command = serializer.to_command()
        flow = SignupFlow()
        context = flow.execute(command)
        return Response({...})
```

**Bước 5:** Đăng ký URL
```python
# application/api/urls.py
urlpatterns = [
    path('identity/', include('application.api.identity.urls')),
    ...,
]
```

**Bước 6:** Viết Test
```python
# Unit test flow (mock handler)
def test_signup_flow():
    mock_handler = Mock()
    flow = SignupFlow(signup_handler=mock_handler)
    context = flow.execute(command)
    assert context.user_id is not None

# Integration test (real module)
@pytest.mark.django_db
def test_signup_api():
    response = client.post('/api/identity/signup/', {...})
    assert response.status_code == 201
```

### 6.2 Khi Nào Tạo Flow vs Direct API Call

| Trường hợp | Pattern |
|-----------|---------|
| Use case đơn giản (1 module call) | Gọi trực tiếp service từ view |
| Use case phức tạp (2+ module, state) | Tạo Flow orchestrator |
| Background job (async task) | Tạo Flow, call từ Celery adapter |
| CLI command | Tạo Flow, call từ CLI adapter |

---

## 7. Hai Luồng Truy Cập Hệ Thống

### 7.1 Luồng Backoffice (Django Admin) – Quản Trị Viên Hệ Thống

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

### 7.2 Luồng Frontend (API) – Khách Hàng

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

## 8. Multi-Tenancy

Nền tảng sử dụng `django-tenants` với cô lập schema-per-tenant:

- **SHARED_APPS**: Public schema (tenants, identity, accounts, `application.flow_rules`)
- **TENANT_APPS**: Tenant schema (mô-đun business; migration chạy per tenant)
- **Middleware**: Giải quyết tenant trước khi API thực thi → mỗi request chạy trong schema đúng

---

## 9. Checklist Khi Thêm Flow Mới

- [ ] Định nghĩa DTO (Command, Context, Result) trong `application/dto/<domain>.py`
- [ ] Định nghĩa Contract/Protocol trong `application/contracts/<domain>.py` (nếu cần decouple)
- [ ] Implement Flow Orchestrator trong `application/flows/<domain>/<flow_name>.py`
- [ ] Tạo API endpoint trong `application/api/<domain>/<endpoint_name>.py`
- [ ] Đăng ký URL trong `application/api/<domain>/urls.py` và include từ `application/api/urls.py`
- [ ] Tạo YAML config trong `application/config/<domain>.yaml` (nếu cần documentation)
- [ ] Viết unit test cho flow (mock handlers)
- [ ] Viết integration test cho API endpoint (real modules)
- [ ] Cập nhật documentation (README này)

| Thành phần | Trách nhiệm | Import | Export |
|---|---|---|---|
| **Domain** | Logic kinh doanh thuần | Không gì | Entity, exception |
| **Repository** | Truy cập dữ liệu trừu tượng | Domain | Interface |
| **Infrastructure** | ORM, admin | Domain, repository | ORM model, admin |
| **Module Service** | Use case mô-đun | Domain, repository | Domain entity, DTO |
| **Application** | Ghép nối mô-đun | Module service (provider) | DTO result |
| **Giao diện** | Dịch input → DTO | Application | JSON/output |

**Nguyên tắc vàng**: Module không bao giờ nhìn thấy Application. Application nhìn thấy mô-đun qua provider. Giao diện nhìn thấy Application. Một chiều, không bao giờ đảo ngược.
