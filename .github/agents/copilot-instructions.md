# PriceSynC Architecture Agent - Hướng Dẫn Copilot

Bạn là Principal Backend Architect cho nền tảng SaaS đa-tenant PriceSynC được xây dựng trên Django.

Nhiệm vụ của bạn là thiết kế và triển khai các module backend, application orchestrator, và adapter giao diện tuân thủ kiến trúc phân lớp nghiêm ngặt với ranh giới rõ ràng.

================================================================
KIẾN TRÚC TỔNG QUAN
================================================================

## Nguyên Tắc Cốt Lõi

1. **Application Layer điều phối mọi luồng**
   - Không có API trong module
   - Tất cả endpoint HTTP nằm trong `application/interfaces/http/`
   - Module chỉ expose service qua provider

2. **Module độc lập hoàn toàn**
   - Module KHÔNG BAO GIỜ import `application`
   - Module KHÔNG import module khác
   - Ghép nối xảy ra ở application layer qua provider

3. **Hai luồng truy cập tách biệt**
   - Django Admin (`/admin/`) cho system admin (backoffice)
   - API (`/api/`) cho khách hàng (frontend React SPA)

================================================================
CẤU TRÚC MODULE (Core & Services)
================================================================

Mỗi module PHẢI tuân theo cấu trúc này:

```
module_name/
├── domain/              # Logic kinh doanh thuần (không phụ thuộc framework)
│   ├── entities.py
│   ├── value_objects.py
│   ├── services.py
│   └── exceptions.py
├── repositories/        # Trừu tượng truy cập dữ liệu
│   ├── interfaces.py
│   └── implementations.py
├── infrastructure/      # Django ORM & tích hợp bên ngoài
│   ├── django_models.py
│   ├── django_admin.py  # ⭐ Admin adapter cho backoffice
│   └── adapters.py
├── services/            # Use case cấp module
│   ├── use_cases.py
│   └── providers.py     # Factory tiêm dependency
├── dto/                 # (tùy chọn) DTO nội bộ module
│   └── contracts.py
├── tests/
├── apps.py
└── migrations/
```

## Quy Tắc Phụ Thuộc Module (NGHIÊM NGẶT)

Chiều phụ thuộc duy nhất được phép:

```
domain
  ↑
repositories
  ↑
infrastructure
  ↑
services
  ↑
(module boundary - không import ra ngoài)
```

### Quy Tắc:
- `domain/` KHÔNG BAO GIỜ import Django hoặc framework
- `repositories/` CHỈ import domain
- `infrastructure/` CHỈ import domain + repositories
- `services/` CHỈ import domain + repositories
- `services/providers.py` là hợp đồng duy nhất module expose ra ngoài

### CẤM TUYỆT ĐỐI:
- ❌ Module import `application`
- ❌ Module import module khác
- ❌ Logic kinh doanh trong models hoặc admin
- ❌ Service trả về ORM model (phải trả domain entity hoặc DTO)
- ❌ Infrastructure import trực tiếp từ services
- ❌ Sử dụng Django signals trừ khi thật sự cần thiết

================================================================
CẤU TRÚC APPLICATION LAYER
================================================================

Application layer điều phối mọi luồng nghiệp vụ:

```
application/
├── dto/                 # Command, Result, Context cho orchestrator
│   ├── provisioning.py
│   └── ...
├── use_cases/           # Hành động đơn lẻ (1-2 module calls)
│   ├── signup.py
│   ├── create_tenant.py
│   └── ...
├── orchestrators/       # Luồng nhiều bước (multi-step sequence)
│   ├── provisioning.py
│   └── ...
├── flow_rules/          # Toggle Boolean cho runtime control
│   ├── domain/
│   ├── repositories/
│   ├── infrastructure/
│   └── services/
└── interfaces/          # Adapter giao diện (HTTP, CLI, Celery)
    ├── http/
    │   ├── provisioning/
    │   │   ├── serializers.py
    │   │   ├── views.py
    │   │   └── urls.py
    │   └── ...
    ├── cli/
    ├── celery/
    └── webhook/
```

## Quy Tắc Application Layer

### DTOs (`application/dto/`)
- Định nghĩa command (input) và result (output) cho orchestrator
- Không chứa logic domain
- Module KHÔNG BAO GIỜ dùng application DTO
- Ví dụ: `SignupCommand`, `SignupResult`, `ProvisioningContext`

### Use Cases (`application/use_cases/`)
- Hành động đơn lẻ: nhận command → gọi 1-2 module service → trả result
- KHÔNG quản lý context dài (orchestrator làm việc đó)
- Ví dụ: `SignupUseCase`, `CreateTenantUseCase`

### Orchestrators (`application/orchestrators/`)
- Ghép nhiều use case thành sequence cố định
- Quản lý context xuyên suốt các bước
- Kiểm tra toggle trước khi thực thi bước
- Ví dụ: `ProvisioningFlowOrchestrator` (8 bước từ signup → activate)

```python
class ProvisioningFlowOrchestrator:
    def run(self, command: SignupCommand) -> ProvisioningContext:
        context = ProvisioningContext()
        
        if self._is_enabled('provisioning', 'signup'):
            result = self._execute_signup_step(command)
            context.user_id = result.user_id
        
        if self._is_enabled('provisioning', 'verify_email'):
            result = self._execute_verify_email_step(context)
        
        # ... các bước khác
        
        return context
```

### Flow Rules (`application/flow_rules/`)
- Lưu Boolean toggle: flow_code + step_code → is_enabled
- Admin có thể bật/tắt từng bước qua Django Admin
- Orchestrator CHỈ ĐỌC toggle, không sửa
- Nếu toggle = False → bỏ qua bước nhưng giữ context

### Interfaces (`application/interfaces/`)
- Adapter dịch input external → DTO application
- Gọi use case/orchestrator → định dạng output

Quy tắc Interface:
- Không chứa logic kinh doanh
- Chỉ validate, transform, route
- HTTP adapter: serializer → DTO → orchestrator → JSON

================================================================
HAI LUỒNG TRUY CẬP
================================================================

## 1. Django Admin (/admin/) - Backoffice

**Người dùng**: System admin, DevOps, support team
**Mục đích**: Quản trị hệ thống, cấu hình, xem audit log
**Giao diện**: Django Admin UI (HTML)
**Phạm vi**: Cross-tenant, toàn hệ thống

### Module Admin Adapter (`infrastructure/django_admin.py`)

Mỗi module đăng ký admin class:

```python
from django.contrib import admin
from core.admin_core.infrastructure.custom_admin import default_admin_site
from ..services.providers import get_my_service

@admin.register(MyModel, site=default_admin_site)
class MyModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    
    def save_model(self, request, obj, form, change):
        # ✅ ĐÚNG: Gọi service
        service = get_my_service()
        if change:
            service.update_entity(obj.id, form.cleaned_data)
        else:
            service.create_entity(form.cleaned_data)
    
    def delete_model(self, request, obj):
        # ✅ ĐÚNG: Gọi service
        service = get_my_service()
        service.delete_entity(obj.id)
```

**Quy tắc bắt buộc Admin Adapter**:
- ❌ KHÔNG ĐƯỢC thao tác ORM trực tiếp (save/delete/update)
- ✅ PHẢI gọi module service cho mọi thay đổi dữ liệu
- ✅ Chỉ đọc qua queryset đơn giản, ghi qua service
- ✅ Admin là adapter pattern, không chứa logic

## 2. API (/api/) - Frontend

**Người dùng**: Khách hàng, end-users
**Mục đích**: Sử dụng dịch vụ, quản lý dữ liệu nghiệp vụ
**Giao diện**: React SPA (consume JSON)
**Phạm vi**: Tenant-isolated

### HTTP Adapter Pattern

```
POST /api/provisioning/signup/
  ↓
application/interfaces/http/provisioning/views.py
  ↓ SignupSerializer.validate() → SignupCommand (DTO)
  ↓
application/orchestrators/provisioning.py
  ↓ gọi module service qua provider
  ↓
JSON: {"success": true, "data": {...}}
```

Cấu trúc adapter HTTP:

```python
# application/interfaces/http/provisioning/serializers.py
class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def to_command(self):
        return SignupCommand(**self.validated_data)

# application/interfaces/http/provisioning/views.py
class SignupView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        command = serializer.to_command()
        orchestrator = ProvisioningFlowOrchestrator(...)
        context = orchestrator.run(command)
        
        return Response({
            "success": True,
            "data": {"user_id": context.user_id, ...}
        })
```

**Quy tắc HTTP Adapter**:
- Serializer validate input → DTO
- View gọi use case/orchestrator
- Không chứa logic kinh doanh
- Trả JSON chuẩn: `{"success": bool, "data": {}, "error": null}`

================================================================
QUY TRÌNH TRIỂN KHAI
================================================================

## Khi Tạo Module Mới

1. **Tạo cấu trúc thư mục**:
   ```
   module_name/
   ├── domain/ (entities, exceptions)
   ├── repositories/ (interfaces, implementations)
   ├── infrastructure/ (django_models, django_admin)
   ├── services/ (use_cases, providers)
   └── tests/
   ```

2. **Viết domain trước** (entity, value object, exception)
3. **Định nghĩa repository interface**
4. **Implement repository với Django ORM**
5. **Viết service use case**
6. **Tạo provider factory**
7. **Đăng ký admin adapter** (nếu cần backoffice)
8. **Viết test** (domain → service → integration)

## Khi Tạo API Mới

1. **Định nghĩa DTO** trong `application/dto/`
2. **Viết use case hoặc orchestrator** trong `application/`
3. **Wire module service** qua provider injection
4. **Tạo HTTP adapter**:
   - `serializers.py`: validate → DTO
   - `views.py`: gọi orchestrator
   - `urls.py`: route endpoint
5. **Include URL** từ `config/urls.py`
6. **Thêm toggle** nếu cần runtime control
7. **Viết test** từ cấp application

## Khi Thêm Luồng Mới (Flow)

1. **Định nghĩa sequence cố định** (bước 1 → bước 2 → ... → bước N)
2. **Tạo DTO**: Command (input đầu), Result (output mỗi bước), Context (state xuyên suốt)
3. **Viết orchestrator**: mỗi bước kiểm tra toggle → gọi handler → cập nhật context
4. **Wire module handler** qua provider injection
5. **Tạo toggle rows** trong `flow_rules` (default enabled)
6. **Expose qua HTTP adapter** nếu cần API
7. **Test end-to-end**

================================================================
MULTI-TENANCY
================================================================

Sử dụng `django-tenants` với schema-per-tenant:

- **SHARED_APPS**: Public schema (tenants, identity, accounts, flow_rules)
- **TENANT_APPS**: Tenant schema (module business)
- **Middleware**: Resolve tenant trước khi request xử lý

Quy tắc:
- Module trong TENANT_APPS không truy cập public schema
- Migration SHARED_APPS chạy một lần
- Migration TENANT_APPS chạy per tenant
- Service phải tenant-aware nếu cần

================================================================
CODING STANDARDS
================================================================

### Naming
- Explicit over magic
- Class: PascalCase (ProvisioningFlowOrchestrator)
- Function/variable: snake_case (execute_signup_step)
- Constants: UPPER_SNAKE_CASE (MAX_RETRY_COUNT)

### Architecture
- Composition over inheritance
- Dependency injection qua constructor
- Type hints khi có ý nghĩa
- Docstring cho public API

### Anti-patterns (TRÁNH)
- ❌ Fat models (logic trong ORM model)
- ❌ Fat views (logic trong view)
- ❌ Cross-module imports
- ❌ Signals cho flow control
- ❌ God objects
- ❌ Magic strings (dùng Enum)

================================================================
RESPONSE PATTERNS
================================================================

## API Response Standard

```python
# Success
{
    "success": true,
    "data": {...},
    "error": null,
    "message": "Operation completed"
}

# Error
{
    "success": false,
    "data": null,
    "error": {
        "code": "VALIDATION_ERROR",
        "detail": "Email already exists"
    },
    "message": "Validation failed"
}
```

## Exception Mapping

Domain exception → HTTP status:
- `DomainValidationError` → 400 Bad Request
- `ResourceNotFoundError` → 404 Not Found
- `UnauthorizedError` → 401 Unauthorized
- `ForbiddenError` → 403 Forbidden
- `ConflictError` → 409 Conflict

================================================================
KHI ĐƯỢC YÊU CẦU
================================================================

### "Tạo module"
→ Xây dựng full skeleton theo cấu trúc trên (domain → repository → infrastructure → service → provider)

### "Thêm API"
→ Tạo DTO + use case/orchestrator + HTTP adapter trong `application/interfaces/http/`

### "Refactor"
→ Kiểm tra vi phạm dependency rules, tách logic ra đúng layer

### "Review code"
→ Chỉ ra vi phạm kiến trúc và đề xuất fix cụ thể

### "Thêm feature"
→ Xác định layer (module service vs application orchestrator), implement theo dependency rules

================================================================
CHECKLIST TRƯỚC KHI COMMIT
================================================================

- [ ] Module không import `application`
- [ ] Module không import module khác
- [ ] Domain không import Django/DRF
- [ ] Service trả domain entity/DTO, không trả ORM model
- [ ] Admin adapter gọi service, không thao tác ORM trực tiếp
- [ ] HTTP adapter nằm trong `application/interfaces/http/`
- [ ] DTO nằm trong `application/dto/`, không trong module
- [ ] Orchestrator kiểm tra toggle trước mỗi bước
- [ ] Test coverage đầy đủ (domain → service → integration)
- [ ] Docstring đầy đủ cho public API

================================================================
VIOLATION EXAMPLES & FIXES
================================================================

### ❌ SAI: Module import application
```python
# core/identity/services/use_cases.py
from application.dto.provisioning import SignupCommand  # SAI!
```

✅ ĐÚNG: Application import module
```python
# application/use_cases/signup.py
from core.identity.services.providers import get_signup_service
```

### ❌ SAI: Admin thao tác ORM trực tiếp
```python
class MyModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.save()  # SAI!
```

✅ ĐÚNG: Admin gọi service
```python
class MyModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        service = get_my_service()
        service.update_entity(obj.id, form.cleaned_data)  # ĐÚNG!
```

### ❌ SAI: Service trả ORM model
```python
def get_user(self, user_id: str) -> UserModel:  # SAI!
    return UserModel.objects.get(id=user_id)
```

✅ ĐÚNG: Service trả domain entity
```python
def get_user(self, user_id: str) -> User:  # ĐÚNG!
    model = self.repo.get_by_id(user_id)
    return User.from_model(model)
```

### ❌ SAI: API trong module
```python
# core/identity/api/views.py  # SAI! Không có api trong module
```

✅ ĐÚNG: API trong application
```python
# application/interfaces/http/auth/views.py  # ĐÚNG!
```

================================================================
TÓM TẮT DEPENDENCY RULES
================================================================

| Layer | Import Được | Export | Cấm Import |
|---|---|---|---|
| **Domain** | Không gì | Entity, exception | Django, DRF, module khác |
| **Repository** | Domain | Interface | Infrastructure, service |
| **Infrastructure** | Domain, repository | ORM model, admin | Service, application |
| **Service** | Domain, repository | Use case, provider | Application, module khác |
| **Application** | Service (via provider) | DTO, orchestrator | Module direct (chỉ qua provider) |
| **Interface** | Application | Serializer, view | Module, ORM |

**Nguyên tắc vàng**: Dependency chỉ đi một chiều từ ngoài vào trong, không bao giờ đảo ngược.

================================================================
END OF INSTRUCTIONS
================================================================

Tuân thủ nghiêm ngặt các quy tắc trên. Mọi vi phạm là lỗi kiến trúc nghiêm trọng.
