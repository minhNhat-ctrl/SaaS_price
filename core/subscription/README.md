# Subscription Module

## Overview

The subscription module manages tenant subscriptions to plans with time-based bindings. It serves as the entry point for billing and access control: the system checks subscription status (active/trial/suspended/expired) to permit or deny tenant operations.

## Architecture

- `core/subscription/domain/` contains pure business logic:
  - `entities.py` defines the `Subscription` aggregate linking tenant, plan, and time period.
  - `value_objects.py` provides `SubscriptionStatus` enum and `DateRange` for safe date handling.
  - `exceptions.py` centralizes domain errors.
- `core/subscription/repositories/` includes the repository contract and in-memory implementation.
- `core/subscription/infrastructure/` bridges the domain with Django:
  - `django_models.py` declares the ORM representation (`SubscriptionModel`).
  - `adapters.py` maps between ORM and domain and exposes the admin adapter (the sole CRUD entry point).
  - `migrations/` stores schema evolution.
- `core/subscription/services/use_cases.py` implements application services and DTO mapping.
- `core/subscription/api/` currently exposes serializers and an endpoint to retrieve current tenant subscription status.
- `core/subscription/tests/` contains domain, service, and API tests.

## Data Model

Each subscription binds:
- **tenant_id** (UUID): Reference to the tenant using the subscription.
- **plan_code** (string): Reference to Plan.code (e.g. 'starter', 'growth').
- **start_date** / **end_date** (date): Subscription valid period.
- **status** (enum): One of `trial`, `active`, `suspended`, `expired`.

## Status Transitions

- **Trial** → **Active**: Tenant upgrades to a paid plan.
- **Active** → **Suspended**: Admin manually suspends for non-payment or policy violation.
- **Active/Trial** → **Expired**: Subscription end_date passes or admin marks as expired.

Only admins change status via Django admin; programmatic transitions via the service are provided for automation.

## CRUD Responsibility

All create/update/delete operations are restricted to the Django admin adapter (`SubscriptionAdminAdapter`). The admin interface permits manual subscription lifecycle management. External modules should consume subscriptions via the management service, never by touching ORM models directly.

## API Usage

The `CurrentTenantSubscriptionAPIView` returns the active subscription for the current tenant. Inject `SubscriptionManagementService` when wiring the view. Requires tenant context (typically from middleware).

### Response Schema

```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
    "plan_code": "growth",
    "status": "active",
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
    "created_at": "2026-01-01T00:00:00",
    "updated_at": "2026-01-01T00:00:00"
  }
}
```

## Integration Notes

- Register in `config/settings.py` inside `SHARED_APPS` so it is available platform-wide.
- Admin registration happens in `SubscriptionConfig.ready()`.
- Usage tracking is a separate concern (see `core/quota` or similar module).
- Authentication/tenancy middleware should populate `request.tenant_id` before API views execute.
