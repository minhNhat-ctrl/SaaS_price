"""
Provisioning Flow API - Implementation Guide

Giới thiệu:
-----------
Provisioning là luồng onboarding chính để các khách hàng đăng ký và tạo tenant.
API này expose luồng đó qua HTTP endpoint /api/provisioning/signup/

Cấu trúc:
---------
✅ application/orchestrators/provisioning.py
   - ProvisioningFlowOrchestrator: Điều phối 8 bước luồng
   - ProvisioningStep enum: Định nghĩa các bước
   - Handler types: Kiểu cho mỗi step handler

✅ application/dto/provisioning.py
   - SignupCommand: DTO đầu vào (email, password, source)
   - ProvisioningContext: Trạng thái luồng (user_id, tenant_id, plan_code, ...)
   - Result DTOs: SignupResult, VerifyEmailResult, CreateTenantResult, ...

✅ application/interfaces/http/provisioning/
   ├── serializers.py: SignupRequestSerializer, ProvisioningContextResponseSerializer
   ├── views.py: ProvisioningSignupView, ProvisioningStatusView
   ├── urls.py: URL routing
   └── providers.py: Orchestrator factory & dependency injection

Luồng HTTP:
-----------
1. Client gửi: POST /api/provisioning/signup/
   {
       "email": "user@example.com",
       "password": "securepassword123",
       "source": "web"
   }

2. SignupRequestSerializer validate request
   → Transform to SignupCommand DTO

3. ProvisioningSignupView.post():
   → Gọi orchestrator.run(command)
   → Orchestrator thực thi 8 bước:
      a. Signup (create user)
      b. Verify Email (xác thực email)
      c. Signin (tạo session)
      d. Create Tenant (tạo tenant)
      e. Resolve Subscription (khởi tạo subscription)
      f. Assign Plan (chọn plan)
      g. Quote Payment (nếu cần, tạo báo giá)
      h. Activate Tenant (kích hoạt tenant)

4. Orchestrator trả ProvisioningContext
   → ProvisioningContextResponseSerializer transform to JSON

5. Response (201 Created):
   {
       "success": true,
       "data": {
           "user_id": "uuid",
           "tenant_id": "uuid",
           "plan_code": "starter",
           "subscription_status": "trial",
           "requires_payment": false,
           "metadata": {...}
       },
       "error": null,
       "message": "Provisioning completed successfully"
   }

Wiring Handlers:
----------------
Mỗi bước cần một handler được tiêm vào orchestrator:

1. Signup Handler:
   async def signup_handler(cmd: SignupCommand) -> SignupResult:
       user = await identity_service.create_user(cmd.email, cmd.password)
       return SignupResult(user_id=user.id, verify_required=True)

2. Verify Email Handler:
   async def verify_handler(ctx: ProvisioningContext) -> VerifyEmailResult:
       verified = await email_service.verify_for_user(ctx.user_id)
       return VerifyEmailResult(verified=verified)

3. Signin Handler:
   async def signin_handler(ctx: ProvisioningContext) -> SigninResult:
       session = await auth_service.create_session(ctx.user_id)
       return SigninResult(user_id=ctx.user_id, session_id=session.id)

4. Create Tenant Handler:
   async def create_tenant_handler(ctx: ProvisioningContext) -> CreateTenantResult:
       tenant = await tenants_service.create_tenant(ctx.user_id)
       return CreateTenantResult(tenant_id=tenant.id, status="created")

5. Resolve Subscription Handler:
   async def resolve_subscription_handler(ctx: ProvisioningContext) -> ResolveSubscriptionResult:
       sub = await subscription_service.resolve(ctx.user_id, ctx.tenant_id)
       return ResolveSubscriptionResult(status="trial", trial_days=14)

6. Assign Plan Handler:
   async def assign_plan_handler(ctx: ProvisioningContext) -> AssignPlanResult:
       plan = await billing_service.assign_default_plan(ctx.tenant_id)
       return AssignPlanResult(plan_code=plan.code, requires_payment=plan.is_paid)

7. Quote Payment Handler:
   async def quote_handler(ctx: ProvisioningContext) -> CreateQuoteResult:
       quote = await billing_service.create_quote(ctx.tenant_id, ctx.plan_code)
       return CreateQuoteResult(quote_id=quote.id, amount=quote.amount, currency="USD")

8. Charge Payment Handler:
   async def charge_handler(ctx: ProvisioningContext) -> ChargePaymentResult:
       txn = await billing_service.charge_payment(ctx.quote_id)
       return ChargePaymentResult(success=txn.status == "completed", transaction_id=txn.id)

9. Activate Tenant Handler:
   async def activate_handler(ctx: ProvisioningContext) -> ActivateTenantResult:
       result = await tenants_service.activate_tenant(ctx.tenant_id)
       return ActivateTenantResult(status="active")

Bước Tiếp Theo:
---------------
1. Tạo providers cho mỗi module (identity, tenants, billing, subscription, email)
   → Mỗi provider expose handler function phù hợp với kiểu mong đợi

2. Tạo apps.py cho application package
   → Khởi tạo ProvisioningOrchestratorProvider với handlers
   → Đăng ký URL routing từ config/urls.py

3. Để include URLs trong config/urls.py:
   urlpatterns = [
       # ...
       path('api/provisioning/', include('application.interfaces.http.provisioning.urls')),
   ]

4. Test end-to-end:
   curl -X POST http://localhost:8000/api/provisioning/signup/ \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com", "password":"securepass123"}'

Quản lý Toggle:
---------------
Django Admin tại /admin/
→ Application → Flow Rule Toggles

Admin có thể bật/tắt từng bước mà không cần sửa code:
- provisioning.signup = True/False
- provisioning.verify_email = True/False
- provisioning.signin = True/False
- ... (tất cả 8 bước)

Nếu bước bị disable:
- Bước sẽ bị bỏ qua nhưng context vẫn chuyển tiếp
- Các bước tiếp theo vẫn được thực thi
- Điều này cho phép phát triển/test từng phần mà không ảnh hưởng toàn bộ luồng

Error Handling:
---------------
Mỗi bước có thể raise exception:
- DomainValidationError → 400 Bad Request
- ResourceNotFoundError → 404 Not Found
- UnauthorizedError → 401 Unauthorized
- Bất kỳ exception nào → HTTP view bắt và trả 400 với error detail

Response format:
{
    "success": false,
    "data": null,
    "error": {
        "code": "ExceptionClassName",
        "detail": "error message"
    },
    "message": "Provisioning failed: error message"
}

Next: Viết use_cases và wire handlers từ core modules.
"""
