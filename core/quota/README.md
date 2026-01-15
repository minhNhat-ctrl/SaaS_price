# Quota & Usage Management Module

**Purpose**: Track runtime usage of plan-limited resources and enforce billing limits in real-time.

This module bridges the Pricing module (defines limits) and Subscription module (binds tenant→plan) by providing operational usage tracking and limit enforcement.

## Architecture

```
Domain Layer
├── UsageRecord (aggregate)    # Tracks tenant's usage for a metric within a period
├── QuotaLimit (entity)        # Defines enforcement policy for a metric
├── UsageEvent (value object)  # Immutable event: metric_code + amount
└── LimitEnforcement (enum)    # HARD | SOFT | NONE

Repository Layer
├── UsageRepository (interface)
└── DjangoORMUsageRepository (impl) + InMemoryUsageRepository (test)

Infrastructure Layer
├── UsageRecordModel (ORM)     # Stores current usage per metric/tenant/period
├── UsageEventModel (ORM)      # Immutable audit trail of all usage events
└── Admin interfaces (read-only)

Services Layer
├── UsageTrackingService       # Record usage + enforce limits
└── QuotaEnforcementService    # Check/apply enforcement policies

API Layer
├── QuotaStatusAPIView         # GET tenant's current usage across all metrics
└── QuotaCheckAPIView          # POST dry-run: would this action exceed limit?
```

## Key Components

### 1. Domain Entities

**UsageRecord** — Aggregate tracking tenant's consumption:
```python
UsageRecord(
    id=UUID,
    tenant_id=UUID,
    metric_code="tracked_products",  # Plan limit identifier
    current_usage=42,                 # Aggregate count
    period_start=datetime,
    period_end=datetime,
)

# Methods:
record_usage(amount=5)     # Increment usage, return new total
reset()                    # Reset to 0 for next period
```

**QuotaLimit** — Enforcement definition:
```python
QuotaLimit(
    metric_code="tracked_products",
    limit_value=100,
    enforcement=LimitEnforcement.HARD  # HARD|SOFT|NONE
)

# Methods:
is_exceeded(current_usage) → bool     # True if usage >= limit
should_enforce(enforcement) → bool    # Check enforcement type
```

**UsageEvent** — Immutable event (for audit trail):
```python
UsageEvent(
    metric_code="tracked_products",
    amount=1,  # Always positive
)

# Validation:
- metric_code required, non-empty
- amount > 0
```

### 2. ORM Models

**UsageRecordModel** — Current consumption snapshot:
```python
UsageRecordModel(
    id=UUID (PK),
    tenant_id=UUID (indexed),
    metric_code=CharField(64),  # e.g., "tracked_products"
    current_usage=IntegerField,
    period_start=DateTimeField,
    period_end=DateTimeField,
    created_at=DateTimeField(auto),
    updated_at=DateTimeField(auto_now),
)

# Indexes:
- (tenant_id, metric_code, period_end)  # Find active period
- (tenant_id, period_end)                # Batch lookups
```

**UsageEventModel** — Immutable event audit trail:
```python
UsageEventModel(
    id=UUID (PK),
    tenant_id=UUID (indexed),
    metric_code=CharField(64),
    amount=IntegerField (default=1),
    metadata=JSONField,  # Context: {"action": "add_product", "resource_id": "..."}
    created_at=DateTimeField(auto, indexed),
)

# Index:
- (tenant_id, metric_code, created_at)  # Audit lookup
```

### 3. Repository Pattern

**UsageRepository** (interface):
```python
class UsageRepository(ABC):
    def list_by_tenant_and_metric(tenant_id, metric_code) → List[UsageRecord]
    def get_current_period(tenant_id, metric_code, period_end) → Optional[UsageRecord]
    def get_by_id(record_id) → Optional[UsageRecord]
    def save(entity: UsageRecord) → UsageRecord
    def delete(record_id) → bool
    def get_for_period(tenant_id, period_start, period_end) → List[UsageRecord]
```

**DjangoORMUsageRepository** (implementation):
- Maps UsageRecordModel ↔ UsageRecord domain entity
- Queries optimized with multi-column indexes
- Returns domain objects only (no ORM instances)

**UsageEventRecorder** (write-only event capture):
```python
UsageEventRecorder.record(
    tenant_id=UUID,
    event=UsageEvent,
    metadata={"action": "..."}  # Optional context
)
# Creates immutable UsageEventModel record
```

### 4. Services (Next Phase)

**UsageTrackingService**:
```python
record_usage(
    tenant_id: UUID,
    event: UsageEvent,
    plan_code: str
) → UsageDTO:
    # 1. Get tenant's subscription (from subscription module)
    # 2. Get plan limits from pricing module
    # 3. Check current usage vs. limit
    # 4. If HARD limit & exceeded: raise QuotaExceededError
    # 5. If SOFT limit: allow + log warning
    # 6. Record usage in db
    # 7. Record immutable event in audit trail
    # 8. Return usage status

enforce_limit(
    tenant_id: UUID,
    metric_code: str,
    limit: QuotaLimit
) → bool:
    # Check if tenant exceeded limit
    # Return True if within limits, raise Exception if HARD limit violated
```

**QuotaEnforcementService**:
```python
check_quota(
    tenant_id: UUID,
    metric_code: str,
    amount: int
) → QuotaCheckDTO:
    # Dry-run: would this usage amount exceed limit?
    # Returns: {exceeded: bool, remaining: int, enforcement: str}
```

### 5. Admin Interface

**UsageRecordAdmin** (read-only):
- List all usage records by tenant, metric, period
- No add/edit/delete (immutable)
- Filterable by metric, period_end, created_at

**UsageEventAdmin** (read-only audit trail):
- List all usage events with context metadata
- Sorted by created_at (newest first)
- No modifications (immutable audit trail)

## Metrics & Limits (From Pricing Module)

Plan defines quotas. Example (Starter plan):
```json
{
  "code": "starter",
  "pricing_rules": {
    "tracked_products": {
      "limit": 50,
      "enforcement": "HARD"
    },
    "price_updates_per_day": {
      "limit": 100,
      "enforcement": "SOFT"
    },
    "team_members": {
      "limit": 2,
      "enforcement": "HARD"
    }
  }
}
```

When tenant is on `starter` plan, all these limits apply.

## Usage Flow

### Recording Usage

```python
# Service records usage
event = UsageEvent(metric_code="tracked_products", amount=1)

usage = usage_service.record_usage(
    tenant_id=tenant_uuid,
    event=event,
    plan_code="starter"
)

# Returns:
# UsageDTO(
#     metric_code="tracked_products",
#     current_usage=42,
#     limit=50,
#     remaining=8,
#     enforcement="HARD",
#     status="within_limit"
# )

# If exceeded:
# raise QuotaExceededError(
#     metric="tracked_products",
#     current=51,
#     limit=50
# )
```

### Checking Before Action (Dry-Run)

```python
# Before user adds 10 new products, check if allowed
would_exceed = quota_service.check_quota(
    tenant_id=tenant_uuid,
    metric_code="tracked_products",
    amount=10  # Hypothetical amount
)

if would_exceed.exceeded and would_exceed.enforcement == "HARD":
    # Block the action
    raise QuotaExceededError(...)
else:
    # Allow action + record usage
    record_usage(event)
```

### Audit Trail

Every usage event is recorded immutably:
```
UsageEventModel(
    tenant_id=...,
    metric_code="tracked_products",
    amount=1,
    metadata={
        "action": "add_product",
        "product_id": "...",
        "triggered_by": "user_123"
    },
    created_at=now
)
```

Enables:
- Usage analytics over time
- Billing audit trail
- Chargeback defense

## Period Management

Usage records are scoped to billing periods:

```python
# Subscription defines period:
subscription = Subscription(
    tenant_id=...,
    plan_code="growth",
    start_date=datetime(2026, 1, 1),
    end_date=datetime(2026, 2, 1)
)

# Usage tracked within period:
usage_record = UsageRecord(
    tenant_id=...,
    metric_code="tracked_products",
    current_usage=42,
    period_start=datetime(2026, 1, 1),
    period_end=datetime(2026, 2, 1)
)

# On new period, reset to 0 and create new record
```

## Enforcement Policies

### HARD Limits
- **Behavior**: Reject action if exceeded
- **Exception**: `QuotaExceededError` raised
- **Example**: `team_members` (can't add user if limit reached)

### SOFT Limits
- **Behavior**: Allow action but log warning
- **Exception**: Not raised, usage recorded
- **Example**: `price_updates_per_day` (monitor but don't block)

### NONE
- **Behavior**: No enforcement, track only
- **Example**: `api_requests` (monitoring metric)

## API Integration (Next Phase)

### GET /api/quota/status/

Current tenant's usage across all metrics:

```json
{
  "success": true,
  "data": {
    "metrics": [
      {
        "metric_code": "tracked_products",
        "current": 42,
        "limit": 50,
        "remaining": 8,
        "enforcement": "HARD",
        "status": "within_limit"
      },
      {
        "metric_code": "team_members",
        "current": 2,
        "limit": 2,
        "remaining": 0,
        "enforcement": "HARD",
        "status": "at_limit"
      }
    ],
    "billing_period": {
      "start": "2026-01-01",
      "end": "2026-02-01"
    }
  }
}
```

### POST /api/quota/check/

Dry-run: would this usage exceed limit?

```json
{
  "metric_code": "tracked_products",
  "amount": 10
}
```

Response:
```json
{
  "success": true,
  "data": {
    "would_exceed": true,
    "current": 42,
    "requested": 10,
    "limit": 50,
    "after_action": 52,
    "enforcement": "HARD",
    "allowed": false
  }
}
```

## Tests

**Domain Tests** (`test_domain.py`):
- UsageRecord: increment, reset, limits
- QuotaLimit: is_exceeded, should_enforce
- UsageEvent: validation

**Service Tests** (`test_services.py`):
- Recording usage within limits
- QuotaExceededError on HARD limit
- Soft limit allows + logs
- Multiple metrics per tenant
- Period rollover

**API Tests** (`test_api.py`):
- QuotaStatusAPIView: current usage
- QuotaCheckAPIView: dry-run checks
- Tenant isolation (can't see other tenant's metrics)

## Migration

```bash
# Migrations created and applied:
python3.9 manage.py migrate quota

# Applied to:
# - Public schema
# - All 51 tenant schemas (auto)
```

## Configuration

No special settings required. Module auto-registers:
- ORM models in public schema
- Django admin in CustomAdminSite
- Admin functions under "Quota & Usage Management"

## Dependency Graph

```
Pricing Module (defines limits per plan)
         ↓
Subscription Module (binds tenant → plan)
         ↓
Quota Module (tracks usage vs. limits)
         ↓
API Layer (exposes quota status to frontend)
```

## Future Extensions

1. **Billing Events**: Emit `QuotaExceededEvent` for billing system
2. **Soft Limit Alerts**: Email notification when at 80% of limit
3. **Grace Period**: Allow 1-5 min overage before blocking
4. **Per-Metric Alerts**: Custom threshold notifications
5. **Historical Analytics**: Usage trends over past periods
6. **Rate Limiting**: Time-window quotas (e.g., 100 req/min)

## File Structure

```
core/quota/
├── domain/
│   ├── __init__.py
│   ├── entities.py          # UsageRecord, QuotaLimit
│   ├── value_objects.py     # UsageEvent, LimitEnforcement
│   └── exceptions.py        # QuotaExceededError, ...
├── repositories/
│   ├── __init__.py
│   ├── interfaces.py        # UsageRepository ABC
│   └── implementations.py   # DjangoORMUsageRepository, UsageEventRecorder
├── infrastructure/
│   ├── __init__.py
│   ├── django_models.py     # UsageRecordModel, UsageEventModel
│   ├── adapters.py          # ORM mappers
│   └── admin.py             # UsageRecordAdmin, UsageEventAdmin
├── services/
│   ├── __init__.py
│   └── use_cases.py         # UsageTrackingService (next phase)
├── api/
│   ├── __init__.py
│   ├── serializers.py       # UsageDTO, QuotaCheckDTO (next phase)
│   ├── views.py             # QuotaStatusAPIView, QuotaCheckAPIView (next phase)
│   └── urls.py              # URL routing (next phase)
├── tests/
│   ├── __init__.py
│   ├── test_domain.py       # Entity & VO tests (next phase)
│   ├── test_services.py     # Service tests (next phase)
│   └── test_api.py          # API tests (next phase)
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py      # ORM models + indexes
├── apps.py                  # QuotaConfig
└── README.md                # This file
```

## Status

✅ **Complete**:
- Domain layer (entities, value objects, exceptions)
- Repository layer (interfaces + ORM implementation)
- Infrastructure layer (ORM models, admin, migrations applied to all schemas)

⏳ **Next**:
- Services layer (usage recording + enforcement)
- API layer (quota status endpoints)
- Tests & comprehensive test coverage
- Billing event emission

---

**Last Updated**: 2026-01-15  
**Quota Module Status**: Core infrastructure ready, services in progress
