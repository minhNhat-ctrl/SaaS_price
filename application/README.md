# Application Layer Documentation

## Tổng Quan

Application layer là tầng điều phối (orchestration layer) giữa external interfaces (HTTP, CLI, Celery) và business modules (core, services). Layer này không chứa logic domain mà chỉ điều phối các module để thực hiện use case.

## Nguyên Tắc Thiết Kế

### 1. Dependency Rule (Quy Tắc Phụ Thuộc)

```
External Interfaces (HTTP/CLI/Celery)
    ↓
Application Layer (orchestration)
    ↓
Business Modules (core/services)
    ↓
Domain Layer
```

**CẤM TUYỆT ĐỐI:**
- ❌ Module KHÔNG ĐƯỢC import application
- ❌ Application KHÔNG ĐƯỢC chứa logic domain
- ❌ API endpoint KHÔNG ĐƯỢC gọi trực tiếp module repository/infrastructure

**BẮT BUỘC:**
- ✅ Application gọi module qua provider pattern
- ✅ API endpoint chỉ gọi flow orchestrator
- ✅ Flow orchestrator điều phối nhiều module service

### 2. Separation of Concerns

| Layer | Trách Nhiệm | Không Được Làm |
|-------|-------------|----------------|
| **api/** | Validate request, gọi flow, format response | Logic domain, gọi trực tiếp repo |
| **flows/** | Điều phối nhiều bước, quản lý state/context | Logic domain, truy cập database |
| **dto/** | Data transfer objects (input/output contract) | Logic, validation phức tạp |
| **contracts/** | Protocol/interface cho flow handler | Implementation cụ thể |
| **config/** | Cấu hình flow (YAML) | Logic thực thi |
| **services/** | Flow context manager, shared utilities | Logic domain |

---

## Cấu Trúc Thư Mục Chi Tiết

### 📁 `application/api/`

**Vai trò:** HTTP API endpoints (controller layer), nhận request từ client (SPA/Mobile), validate, gọi flow, trả response JSON.

**Cấu trúc:**
```
api/
├── identity/          # Authentication & authorization endpoints
│   ├── signup.py      # POST /api/identity/signup/
│   ├── signin.py      # POST /api/identity/signin/
│   └── recover_password.py
│
├── provisioning/      # Tenant provisioning endpoints
│   └── create_tenant.py
│
├── business/          # Business operations endpoints
│   └── create_product.py
│
└── urls.py            # URL router tổng hợp tất cả sub-apps
```

**Pattern:**
```python
# api/identity/signup.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ...flows.identity.signup_flow import SignupFlow
from ...dto.identity import SignupCommand


class SignupAPIView(APIView):
    """API endpoint for user signup."""
    
    def post(self, request):
        # 1. Validate & parse request → Command DTO
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        command = SignupCommand(**serializer.validated_data)
        
        # 2. Execute flow
        flow = SignupFlow()
        context = flow.execute(command)
        
        # 3. Format & return response
        return Response({
            "success": True,
            "data": {
                "user_id": str(context.user_id),
                "email": context.email,
                "requires_verification": context.requires_verification
            },
            "error": None,
            "message": "Signup successful"
        }, status=status.HTTP_201_CREATED)
```

**Quy tắc:**
- Một file = một endpoint/resource
- Không chứa logic, chỉ validate → call flow → format response
- Trả về chuẩn: `{"success": bool, "data": {}, "error": null, "message": str}`
- Exception được catch bởi middleware/exception handler

---

### 📁 `application/flows/`

**Vai trò:** Flow orchestrator, điều phối nhiều bước (multi-step sequence), quản lý context/state xuyên suốt các bước.

**Cấu trúc:**
```
flows/
├── identity/
│   ├── signup_flow.py              # 3 steps: validate → create user → send email
│   ├── verify_email_flow.py        # 2 steps: verify token → activate account
│   └── recover_password_flow.py
│
├── provisioning/
│   └── tenant_onboarding_flow.py   # 8 steps: signup → tenant → plan → billing...
│
├── business/
│   └── create_product_flow.py
│
└── system/
    └── expire_subscription_flow.py  # Background job flow
```

**Pattern:**
```python
# flows/identity/signup_flow.py
from dataclasses import dataclass
from typing import Optional

from ...dto.identity import SignupCommand, SignupContext
from ...contracts.identity import SignupHandlerProtocol
from core.identity.services.providers import get_signup_service
from core.notification.services.providers import get_email_service


@dataclass
class SignupFlow:
    """
    Flow: User Signup
    Steps:
        1. Validate email uniqueness
        2. Create user account
        3. Send verification email
    """
    
    # Inject handlers (hoặc lazy load từ provider)
    signup_handler: Optional[SignupHandlerProtocol] = None
    
    def execute(self, command: SignupCommand) -> SignupContext:
        """Execute full signup flow."""
        context = SignupContext()
        
        # Step 1: Validate email (call identity module)
        signup_service = self.signup_handler or get_signup_service()
        is_unique = signup_service.check_email_unique(command.email)
        if not is_unique:
            raise ValueError("Email already exists")
        
        # Step 2: Create user
        user = signup_service.create_user(
            email=command.email,
            password=command.password
        )
        context.user_id = user.id
        context.email = user.email
        
        # Step 3: Send verification email
        email_service = get_email_service()
        token = email_service.send_verification_email(user.email)
        context.verification_token = token
        context.requires_verification = True
        
        return context
```

**Quy tắc:**
- Flow là sequence cố định (bước 1 → 2 → 3 → ...)
- Mỗi bước gọi một hoặc nhiều module service
- Context lưu state xuyên suốt các bước
- Handler được inject qua constructor (dependency injection) hoặc lazy load từ provider
- KHÔNG truy cập database/ORM trực tiếp, chỉ gọi service

**Khi nào tạo Flow:**
- Use case cần nhiều hơn 2 module service
- Cần quản lý state/context phức tạp
- Cần rollback/compensation khi lỗi
- Background job cần chạy nhiều bước

---

### 📁 `application/dto/`

**Vai trò:** Data Transfer Objects (DTO), định nghĩa contract input/output giữa API ↔ Flow ↔ Module.

**Cấu trúc:**
```
dto/
├── identity.py     # SignupCommand, SignupResult, SignupContext
├── tenant.py       # CreateTenantCommand, TenantContext
├── billing.py      # CreateInvoiceCommand, PaymentResult
└── product.py      # CreateProductCommand, ProductResult
```

**Pattern:**
```python
# dto/identity.py
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class SignupCommand:
    """Input DTO for signup flow."""
    email: str
    password: str
    full_name: Optional[str] = None
    referral_code: Optional[str] = None


@dataclass
class SignupContext:
    """Context carries state across signup flow steps."""
    user_id: Optional[str] = None
    email: Optional[str] = None
    verification_token: Optional[str] = None
    requires_verification: bool = False
    tenant_id: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class SignupResult:
    """Output DTO for signup flow."""
    user_id: str
    email: str
    requires_verification: bool
    message: str
```

**Quy tắc:**
- Immutable nếu có thể (frozen=True)
- Không chứa logic (chỉ data container)
- Command = input từ client
- Context = state xuyên suốt flow
- Result = output trả về client
- Dùng type hints đầy đủ

---

### 📁 `application/contracts/`

**Vai trò:** Protocol/Interface definition cho flow handlers, định nghĩa contract mà module service phải implement.

**Cấu trúc:**
```
contracts/
├── identity.py       # SignupHandlerProtocol, SigninHandlerProtocol
├── provisioning.py   # TenantCreationHandlerProtocol
└── business.py       # ProductCreationHandlerProtocol
```

**Pattern:**
```python
# contracts/identity.py
from typing import Protocol
from ...dto.identity import SignupCommand, SignupResult


class SignupHandlerProtocol(Protocol):
    """Contract for signup handler (implemented by identity module)."""
    
    def check_email_unique(self, email: str) -> bool:
        """Check if email is not taken."""
        ...
    
    def create_user(self, email: str, password: str) -> SignupResult:
        """Create new user account."""
        ...
    
    def send_verification_email(self, user_id: str, email: str) -> str:
        """Send verification email, return token."""
        ...
```

**Quy tắc:**
- Dùng `typing.Protocol` (Python 3.8+) hoặc `abc.ABC`
- Chỉ định nghĩa method signature, không implement
- Module service implement protocol này
- Flow chỉ depend vào Protocol, không depend vào implementation cụ thể

---

### 📁 `application/config/`

**Vai trò:** Cấu hình flow (YAML), toggle enable/disable bước, timeout, retry policy.

**Cấu trúc:**
```
config/
├── provisioning.yaml    # Provisioning flow config
├── billing.yaml         # Billing flow config
└── subscription.yaml    # Subscription flow config
```

**Pattern:**
```yaml
# config/provisioning.yaml
flow_code: "provisioning"
description: "Tenant onboarding flow"

steps:
  - code: "signup"
    enabled: true
    timeout_seconds: 30
    retry_policy:
      max_retries: 3
      backoff: "exponential"
  
  - code: "create_tenant"
    enabled: true
    timeout_seconds: 60
    
  - code: "select_plan"
    enabled: true
    
  - code: "create_billing"
    enabled: false  # Skip billing for MVP
    
  - code: "send_welcome_email"
    enabled: true
    timeout_seconds: 15

metadata:
  owner: "platform-team"
  last_updated: "2026-01-19"
```

**Quy tắc:**
- YAML cho dễ đọc và chỉnh sửa
- Mỗi flow một file
- Flow orchestrator đọc config lúc runtime
- Admin có thể toggle enable/disable bước mà không cần deploy code

---

### 📁 `application/services/`

**Vai trò:** Shared utilities cho application layer (flow context manager, config loader, logger).

**Cấu trúc:**
```
services/
├── flow_context.py      # FlowContext manager
├── config_loader.py     # Load YAML config
└── flow_logger.py       # Flow execution logger
```

**Pattern:**
```python
# services/flow_context.py
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime


@dataclass
class FlowContext:
    """Generic flow execution context."""
    flow_code: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def mark_step_start(self, step_code: str):
        self.current_step = step_code
        self.metadata[f"{step_code}_started_at"] = datetime.utcnow()
    
    def mark_step_complete(self, step_code: str):
        self.metadata[f"{step_code}_completed_at"] = datetime.utcnow()
    
    def mark_complete(self):
        self.completed_at = datetime.utcnow()
```

---

## Hướng Dẫn Tạo Flow Mới

### Bước 1: Định Nghĩa DTO

```python
# application/dto/business.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class CreateProductCommand:
    name: str
    price: float
    tenant_id: str
    category: Optional[str] = None

@dataclass
class CreateProductContext:
    product_id: Optional[str] = None
    tenant_id: Optional[str] = None
    validation_passed: bool = False

@dataclass
class CreateProductResult:
    product_id: str
    name: str
    message: str
```

### Bước 2: Định Nghĩa Contract (nếu cần)

```python
# application/contracts/business.py
from typing import Protocol
from ..dto.business import CreateProductResult

class ProductCreationHandlerProtocol(Protocol):
    def validate_product_name(self, name: str, tenant_id: str) -> bool:
        ...
    
    def create_product(self, command: CreateProductCommand) -> CreateProductResult:
        ...
```

### Bước 3: Tạo Flow Orchestrator

```python
# application/flows/business/create_product_flow.py
from dataclasses import dataclass
from typing import Optional

from ...dto.business import CreateProductCommand, CreateProductContext
from ...contracts.business import ProductCreationHandlerProtocol
from services.products.services.providers import get_product_service


@dataclass
class CreateProductFlow:
    """
    Flow: Create Product
    Steps:
        1. Validate product name uniqueness
        2. Create product in tenant schema
        3. Publish product creation event
    """
    
    handler: Optional[ProductCreationHandlerProtocol] = None
    
    def execute(self, command: CreateProductCommand) -> CreateProductContext:
        context = CreateProductContext(tenant_id=command.tenant_id)
        
        # Step 1: Validate
        product_service = self.handler or get_product_service()
        is_unique = product_service.validate_product_name(
            command.name, 
            command.tenant_id
        )
        if not is_unique:
            raise ValueError("Product name already exists")
        context.validation_passed = True
        
        # Step 2: Create product
        result = product_service.create_product(command)
        context.product_id = result.product_id
        
        # Step 3: Publish event (optional)
        # event_service.publish("product.created", context.product_id)
        
        return context
```

### Bước 4: Tạo API Endpoint

```python
# application/api/business/create_product.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers, status

from ...flows.business.create_product_flow import CreateProductFlow
from ...dto.business import CreateProductCommand


class CreateProductSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    category = serializers.CharField(required=False)


class CreateProductAPIView(APIView):
    """POST /api/business/products/"""
    
    def post(self, request):
        serializer = CreateProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get tenant_id from request context (middleware sets it)
        tenant_id = request.tenant.id
        
        command = CreateProductCommand(
            tenant_id=tenant_id,
            **serializer.validated_data
        )
        
        flow = CreateProductFlow()
        context = flow.execute(command)
        
        return Response({
            "success": True,
            "data": {
                "product_id": context.product_id,
                "tenant_id": context.tenant_id
            },
            "error": None,
            "message": "Product created successfully"
        }, status=status.HTTP_201_CREATED)
```

### Bước 5: Đăng Ký URL

```python
# application/api/business/urls.py
from django.urls import path
from .create_product import CreateProductAPIView

urlpatterns = [
    path('products/', CreateProductAPIView.as_view(), name='create_product'),
]
```

```python
# application/api/urls.py
from django.urls import path, include

urlpatterns = [
    path('identity/', include('application.api.identity.urls')),
    path('provisioning/', include('application.api.provisioning.urls')),
    path('business/', include('application.api.business.urls')),  # Add this
]
```

### Bước 6: Test Flow

```python
# application/flows/business/tests/test_create_product_flow.py
import pytest
from unittest.mock import Mock
from ..create_product_flow import CreateProductFlow
from ...dto.business import CreateProductCommand


def test_create_product_flow_success():
    # Mock handler
    mock_handler = Mock()
    mock_handler.validate_product_name.return_value = True
    mock_handler.create_product.return_value = Mock(product_id="prod_123")
    
    # Execute flow
    flow = CreateProductFlow(handler=mock_handler)
    command = CreateProductCommand(
        name="Test Product",
        price=99.99,
        tenant_id="tenant_123"
    )
    context = flow.execute(command)
    
    # Assert
    assert context.validation_passed is True
    assert context.product_id == "prod_123"
    mock_handler.validate_product_name.assert_called_once()
    mock_handler.create_product.assert_called_once()
```

---

## Tương Tác Với Module

### Pattern 1: Provider Pattern (Recommended)

```python
# Module expose service qua provider
# core/identity/services/providers.py
def get_signup_service() -> SignupService:
    repo = DjangoUserRepository()
    return SignupService(repository=repo)

# Application gọi qua provider
# application/flows/identity/signup_flow.py
from core.identity.services.providers import get_signup_service

def execute(self, command):
    service = get_signup_service()
    user = service.create_user(...)
```

### Pattern 2: Dependency Injection

```python
# Flow nhận handler qua constructor
@dataclass
class SignupFlow:
    signup_handler: SignupHandlerProtocol
    email_handler: EmailHandlerProtocol
    
    def execute(self, command):
        user = self.signup_handler.create_user(...)
        self.email_handler.send_verification(user.email)

# Inject lúc khởi tạo (trong apps.py hoặc factory)
flow = SignupFlow(
    signup_handler=get_signup_service(),
    email_handler=get_email_service()
)
```

### Pattern 3: Lazy Loading

```python
@dataclass
class SignupFlow:
    _signup_service: Optional[SignupService] = None
    
    @property
    def signup_service(self):
        if self._signup_service is None:
            self._signup_service = get_signup_service()
        return self._signup_service
```

---

## Testing Strategy

### Unit Test Flow (Mock Handlers)

```python
def test_signup_flow():
    mock_handler = Mock()
    flow = SignupFlow(signup_handler=mock_handler)
    context = flow.execute(command)
    assert context.user_id is not None
```

### Integration Test Flow (Real Modules)

```python
@pytest.mark.django_db
def test_signup_flow_integration():
    flow = SignupFlow()  # Use real providers
    command = SignupCommand(email="test@example.com", password="pass")
    context = flow.execute(command)
    assert User.objects.filter(email="test@example.com").exists()
```

### API Test (End-to-End)

```python
def test_signup_api(client):
    response = client.post('/api/identity/signup/', {
        'email': 'test@example.com',
        'password': 'Secure123!'
    })
    assert response.status_code == 201
    assert response.json()['success'] is True
```

---

## Checklist Khi Thêm Flow Mới

- [ ] Định nghĩa DTO (Command, Context, Result) trong `application/dto/`
- [ ] Định nghĩa Contract/Protocol trong `application/contracts/` (nếu cần)
- [ ] Implement Flow Orchestrator trong `application/flows/`
- [ ] Tạo API endpoint trong `application/api/`
- [ ] Đăng ký URL trong `application/api/urls.py`
- [ ] Tạo YAML config trong `application/config/` (nếu cần toggle)
- [ ] Viết unit test cho flow
- [ ] Viết integration test cho API endpoint
- [ ] Update documentation (README.md này)

---

## Best Practices

### DO ✅

- Flow orchestrator chỉ điều phối, không chứa logic domain
- Dùng DTO rõ ràng cho input/output
- Inject dependency qua constructor
- Log mỗi bước của flow
- Handle exception gracefully
- Test flow với mock handlers trước khi test integration

### DON'T ❌

- Gọi trực tiếp ORM model từ flow
- Import module infrastructure vào application
- Hardcode config trong flow
- Skip validation ở API layer
- Trả về ORM model từ flow (phải DTO)
- Tạo circular dependency (module → application)

---

## Migration từ Cấu Trúc Cũ

Nếu bạn đang migrate từ cấu trúc cũ:

```
OLD: application/orchestrators/provisioning.py
NEW: application/flows/provisioning/tenant_onboarding_flow.py

OLD: application/interfaces/http/provisioning/views.py
NEW: application/api/provisioning/create_tenant.py

OLD: application/dto/provisioning.py (monolithic)
NEW: application/dto/identity.py, tenant.py, billing.py (split by domain)
```

**Lý do refactor:**
- Tách rõ domain (identity, provisioning, business)
- Một file = một endpoint/flow (Single Responsibility)
- Dễ scale và maintain
- Tuân thủ DDD bounded context

---

## FAQ

**Q: Khi nào cần tạo flow mới?**
A: Khi use case cần gọi >= 2 module services hoặc cần quản lý state phức tạp.

**Q: Flow và Use Case khác nhau thế nào?**
A: Use Case = hành động đơn lẻ (1 module call). Flow = sequence nhiều use cases (multi-module).

**Q: API có thể gọi trực tiếp module service không?**
A: Được nếu use case đơn giản (CRUD 1 entity). Nhưng nên qua flow để dễ mở rộng sau.

**Q: DTO và Serializer khác nhau thế nào?**
A: Serializer (DRF) validate HTTP request. DTO truyền data giữa layer. API dùng serializer → DTO → flow.

**Q: Có cần contract/protocol không?**
A: Không bắt buộc. Dùng khi muốn decouple hoàn toàn (testability) hoặc có nhiều implementation.

---

## Summary

Application layer là **orchestration layer**, không chứa logic domain. Nhiệm vụ chính:

1. **API** (`api/`): Validate request, gọi flow, format response
2. **Flow** (`flows/`): Điều phối nhiều module, quản lý context
3. **DTO** (`dto/`): Contract input/output giữa các layer
4. **Contract** (`contracts/`): Interface cho module handlers
5. **Config** (`config/`): Toggle flow steps qua YAML
6. **Services** (`services/`): Shared utilities (context manager, logger)

**Golden Rule:** Application phụ thuộc vào Module, KHÔNG BAO GIỜ ngược lại.
