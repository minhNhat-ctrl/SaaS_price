# Module Inventory & Application Integration Plan

**Mục đích:** Liệt kê các module hiện có, use case của chúng, và xác định workflow nào cần application orchestration.

---

## Core Modules (core/)

### 1. core/identity
**Trách nhiệm:** Authentication, user management (django-allauth)  
**Use cases hiện có:**
- Signup (tạo user mới)
- Login/Logout
- Change password
- Check authentication status

**Cần application orchestration:**
- ✅ **Signup** → cần ghép với tenant provisioning + subscription + billing + notification
- ❌ Login/Logout → độc lập, giữ nguyên
- ❌ Change password → độc lập

**Module service interface cần expose:**
```python
# core.identity.services.use_cases
class CreateUserUseCase:
    def execute(email, password, **kwargs) -> User
```

---

### 2. core/tenants
**Trách nhiệm:** Multi-tenancy, tenant provisioning, domain mapping  
**Use cases hiện có:**
- Create tenant
- Assign domain to tenant
- List/manage tenants (admin)

**Cần application orchestration:**
- ✅ **Create tenant** → luôn được gọi từ signup workflow
- ❌ Admin operations → độc lập

**Module service interface cần expose:**
```python
# core.tenants.services.use_cases
class CreateTenantUseCase:
    def execute(tenant_name, schema_name, user) -> Tenant

class AssignDomainUseCase:
    def execute(tenant, domain) -> TenantDomain
```

---

### 3. core/access
**Trách nhiệm:** RBAC (roles, permissions, policies, memberships)  
**Use cases hiện có:**
- Create membership (assign user to tenant with role)
- Assign role/permissions
- Check permissions

**Cần application orchestration:**
- ✅ **Create membership** → gọi sau khi tenant provisioned (trong signup flow)
- ❌ Permission checks → độc lập

**Module service interface cần expose:**
```python
# core.access.services.use_cases
class CreateMembershipUseCase:
    def execute(tenant, user, role='owner') -> Membership
```

---

### 4. core/accounts
**Trách nhiệm:** User profiles, preferences, avatars, notification settings  
**Use cases hiện có:**
- Create/update profile
- Manage preferences (theme, language)
- Upload avatar

**Cần application orchestration:**
- ✅ **Create profile** → gọi trong signup workflow (sau create user)
- ❌ Update operations → độc lập

**Module service interface cần expose:**
```python
# core.accounts.services.use_cases
class CreateProfileUseCase:
    def execute(user, tenant, **profile_data) -> UserProfile
```

---

### 5. core/pricing
**Trách nhiệm:** Plan definitions, feature limits, pricing tiers  
**Use cases hiện có:**
- List available plans
- Get plan details
- Check feature availability for plan

**Cần application orchestration:**
- ❌ Tất cả đều read-only → độc lập
- ✅ Nhưng subscription workflow cần query pricing để validate plan

**Module service interface cần expose:**
```python
# core.pricing.services.use_cases
class GetPlanUseCase:
    def execute(plan_id) -> Plan

class ListAvailablePlansUseCase:
    def execute() -> List[Plan]
```

---

### 6. core/subscription
**Trách nhiệm:** Tenant ↔ Plan binding, subscription lifecycle  
**Use cases hiện có:**
- Assign plan to tenant
- Change plan (upgrade/downgrade)
- Cancel subscription
- Check subscription status

**Cần application orchestration:**
- ✅ **Assign default plan** → trong signup workflow
- ✅ **Change plan** → trigger quota update + billing update + notification
- ✅ **Cancel** → trigger quota cleanup + billing finalization

**Module service interface cần expose:**
```python
# core.subscription.services.use_cases
class AssignPlanUseCase:
    def execute(tenant, plan) -> Subscription

class ChangePlanUseCase:
    def execute(tenant, new_plan) -> Subscription

class CancelSubscriptionUseCase:
    def execute(tenant) -> Subscription
```

---

### 7. core/quota
**Trách nhiệm:** Usage tracking, limit enforcement, quota initialization  
**Use cases hiện có:**
- Initialize quota for tenant (based on plan)
- Track usage
- Check if limit exceeded
- Reset quota

**Cần application orchestration:**
- ✅ **Initialize quota** → trong signup workflow (sau assign plan)
- ✅ **Update quota** → khi change plan
- ❌ Track/check operations → độc lập (gọi trực tiếp từ business logic)

**Module service interface cần expose:**
```python
# core.quota.services.use_cases
class InitializeQuotaUseCase:
    def execute(tenant, plan) -> List[QuotaLimit]

class UpdateQuotaLimitsUseCase:
    def execute(tenant, plan) -> List[QuotaLimit]
```

---

### 8. core/billing
**Trách nhiệm:** Invoice, payment, billing contract, provider integration  
**Use cases hiện có:**
- Create billing contract (contract-centric)
- Record payment
- Generate invoice
- Sync with payment provider

**Cần application orchestration:**
- ✅ **Create contract** → trong signup workflow (sau assign plan)
- ✅ **Payment confirmed** → trigger subscription update + notification
- ✅ **Payment failed** → trigger quota suspension + notification

**Module service interface cần expose:**
```python
# core.billing.services.use_cases
class CreateBillingContractUseCase:
    def execute(tenant, plan, provider) -> BillingContract

class RecordPaymentUseCase:
    def execute(contract, amount, provider_payment_id) -> Payment

class HandlePaymentWebhookUseCase:
    def execute(provider, event_data) -> PaymentEvent
```

---

### 9. core/notification
**Trách nhiệm:** Send email/SMS/push, template management, audit log  
**Use cases hiện có:**
- Send notification (email, SMS, push)
- Manage templates (admin only)
- View notification logs

**Cần application orchestration:**
- ✅ **Send notification** → luôn được gọi bởi application workflows (signup, payment, subscription events)
- ❌ Template/log management → admin only

**Module service interface cần expose:**
```python
# core.notification.services.use_cases
class NotificationService:
    def send(command: SendCommand) -> NotificationLog
```

---

### 10. core/admin_core
**Trách nhiệm:** Custom Django admin loader, admin module discovery  
**Use cases hiện có:**
- Auto-register admin models
- Admin authentication/authorization

**Cần application orchestration:**
- ❌ Không có → infrastructure thuần

---

## Services Modules (services/)

### 11. services/products
**Trách nhiệm:** Tenant product management, catalog  
**Use cases hiện có:**
- Create/update/delete product
- List products
- Search products

**Cần application orchestration:**
- ❌ Hầu hết độc lập (CRUD thuần)
- ✅ **Bulk import** → có thể cần notification khi hoàn thành
- ✅ **Price change** → log to price_history (products_shared)

**Module service interface cần expose:**
```python
# services.products.services.use_cases
class CreateProductUseCase:
    def execute(tenant, product_data) -> Product

class BulkImportProductsUseCase:
    def execute(tenant, csv_file) -> ImportResult
```

---

### 12. services/products_shared
**Trách nhiệm:** Shared product data (ProductURL, PriceHistory, Domain) - public schema  
**Use cases hiện có:**
- Track product URL across tenants
- Record price history
- Manage domains

**Cần application orchestration:**
- ❌ Hầu hết độc lập
- ✅ **Add URL** → có thể trigger crawl_service

**Module service interface cần expose:**
```python
# services.products_shared.services.use_cases
class AddProductURLUseCase:
    def execute(url, domain, tenant) -> ProductURL
```

---

### 13. services/crawl_service
**Trách nhiệm:** Web scraping, price monitoring, auto-record scheduler  
**Use cases hiện có:**
- Schedule crawl jobs
- Execute crawl
- Auto-record price changes

**Cần application orchestration:**
- ❌ Background service chủ yếu
- ✅ **Manual trigger crawl** → có thể notification khi done

**Module service interface cần expose:**
```python
# services.crawl_service.services.use_cases
class TriggerCrawlUseCase:
    def execute(product_url_id, tenant) -> CrawlJob
```

---

## Application Workflows Cần Thiết

### Workflow 1: Tenant Onboarding (Signup) ⭐ PRIORITY 1
**Modules tham gia:** identity → tenants → access → accounts → pricing → subscription → quota → billing → notification

**Luồng:**
1. `identity`: Create user
2. `tenants`: Create tenant + assign domain
3. `access`: Create membership (user as owner)
4. `accounts`: Create default profile
5. `pricing`: Get default plan (free tier)
6. `subscription`: Assign plan to tenant
7. `quota`: Initialize quota based on plan
8. `billing`: Create billing contract
9. `notification`: Send welcome email

**Application use case:**
```python
# application/use_cases/onboarding/tenant_signup.py
class TenantSignupUseCase(ApplicationUseCase):
    def execute(email, password, tenant_name, domain):
        # Orchestrate all 9 steps
        # Handle rollback if any step fails
        # Return UseCaseResult
```

---

### Workflow 2: Subscription Change ⭐ PRIORITY 2
**Modules tham gia:** subscription → quota → billing → notification

**Luồng:**
1. `subscription`: Change plan
2. `quota`: Update limits
3. `billing`: Update contract
4. `notification`: Send confirmation email

**Application use case:**
```python
# application/use_cases/subscription/change_plan.py
class ChangePlanUseCase(ApplicationUseCase):
    def execute(tenant, new_plan):
        # Orchestrate plan change
        # Prorated billing if applicable
```

---

### Workflow 3: Payment Webhook Processing ⭐ PRIORITY 3
**Modules tham gia:** billing → subscription → notification

**Luồng:**
1. `billing`: Parse webhook, record payment/event
2. `subscription`: Update status if needed (unpaid → active)
3. `notification`: Send receipt email

**Application orchestrator:**
```python
# application/orchestrators/payment_webhook.py
class PaymentWebhookOrchestrator(Orchestrator):
    def run(provider, webhook_payload):
        # Async/background processing
        # Idempotent (check if already processed)
```

---

### Workflow 4: Quota Exceeded Notification
**Modules tham gia:** quota → notification

**Luồng:**
1. `quota`: Detect limit exceeded
2. `notification`: Send alert email

**Application use case:**
```python
# application/use_cases/quota/notify_limit_exceeded.py
class NotifyQuotaExceededUseCase(ApplicationUseCase):
    def execute(tenant, quota_type):
        # Send notification
```

---

## Rollout Plan

### Phase 1: Foundation (Week 1-2)
- [x] Create application/ structure
- [x] Document architecture
- [ ] Create MODULE_INVENTORY.md (this file)
- [ ] Define module service interfaces (contracts)

### Phase 2: First Workflow (Week 3-4)
- [ ] Implement TenantSignupUseCase
- [ ] Ensure all module services expose required use cases
- [ ] Refactor `/api/identity/signup/` to call TenantSignupUseCase
- [ ] Test end-to-end

### Phase 3: Core Workflows (Week 5-8)
- [ ] Implement ChangePlanUseCase
- [ ] Implement PaymentWebhookOrchestrator
- [ ] Refactor related API endpoints

### Phase 4: Gradual Migration (Week 9+)
- [ ] Identify remaining multi-module flows
- [ ] Create application use cases
- [ ] Refactor API views one by one
- [ ] Document patterns

---

## Checklist: Module Service Contract

Mỗi module cần đảm bảo:
- [ ] File `services/use_cases.py` tồn tại
- [ ] Các class use case có tên rõ ràng (VerbNounUseCase)
- [ ] Input là dict/value object, không phải request
- [ ] Output là domain entity/DTO, không phải ORM model
- [ ] Use case không biết HTTP, chỉ nhận tenant + data
- [ ] Exception rõ ràng (domain exception)

---

## Next Actions

1. ✅ Review inventory này với team
2. ⏳ Định nghĩa interface contract cho từng module service (trong từng module README hoặc services/__init__.py)
3. ⏳ Implement TenantSignupUseCase đầu tiên
4. ⏳ Refactor signup endpoint làm proof-of-concept
5. ⏳ Document pattern và replicate cho workflows khác
