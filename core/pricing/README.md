# Pricing Module

## Overview

The pricing module manages SaaS subscription plan definitions, including limits and pricing rules. It is treated as shared infrastructure (lives in public schema) and follows the core layered architecture: domain → repositories → infrastructure → services → api.

## Folder Structure

- `core/pricing/domain/` contains pure business logic:
  - `entities.py` defines the `Plan` aggregate and lifecycle helpers.
  - `value_objects.py` provides `BillingCycle`, `Money`, `PlanLimit`, and `PricingRule` objects.
  - `services.py` offers the lightweight `PlanCatalog` helper for in-memory lookups.
  - `exceptions.py` centralizes domain-specific errors.
- `core/pricing/repositories/` includes the repository contract and an in-memory implementation used by tests and bootstrap flows.
- `core/pricing/infrastructure/` bridges the domain with Django:
  - `django_models.py` declares the ORM representation (`PlanModel`).
  - `adapters.py` maps between ORM and domain and exposes the admin adapter (the sole CRUD entry point).
  - `migrations/` stores schema evolution.
- `core/pricing/services/use_cases.py` implements application services, default plan definitions, and DTO mapping.
- `core/pricing/api/` currently exposes serializers and a read-only API view scaffold (no public URL wiring yet).
- `core/pricing/tests/` contains domain, service, and serializer tests.

## CRUD Responsibility

All create/update/delete operations are restricted to the Django admin adapter (`PlanAdminAdapter`). It constructs domain objects and persists through the repository layer, ensuring the domain model remains the source of truth. External modules should consume plans via the catalog service, never by touching ORM models directly.

## Default Plans & Limits

`use_cases.py` embeds default plan definitions (`starter`, `growth`, `enterprise`). Limits describe usage caps (tracked products, price updates, team members, etc.), while pricing rules capture overage or contract notes. The service can bootstrap these definitions into the repository on demand (`ensure_default_plans`).

## Service Usage

To read plans, instantiate `PlanCatalogService` with a `PlanRepository` (typically `DjangoORMPlanRepository`). Use `list_active_plans()` for tenant-facing catalog display or `get_plan(code)` when resolving subscriptions. The service returns simple DTOs detached from persistence.

## API Layer

`PlanCatalogAPIView` demonstrates how to expose plan listings. It requires dependency injection of a pre-configured `PlanCatalogService` instance. The module avoids binding to Django views directly, keeping the api layer thin.

### Frontend Integration Notes

- **View class**: `PlanCatalogAPIView` (read-only). Inject an instance of `PlanCatalogService` when wiring the view (see `core/pricing/api/urls.py` factory helper).
- **Typical endpoint**: expose through a URL such as `/api/pricing/plans/` by including the URL pattern returned from `build_urls(service=PlanCatalogService(repository))` inside your project router.
- **Authentication/tenancy**: the view is agnostic; wrap it with middleware appropriate for your frontend context (e.g., tenant-aware routing, auth decorators).
- **Response schema**:

```json
{
  "success": true,
  "data": [
    {
      "code": "starter",
      "name": "Starter",
      "description": "Free tier for evaluation and small projects.",
      "currency": "USD",
      "amount": "0.00",
      "billing_cycle": "monthly",
      "limits": [
        {
          "code": "tracked_products",
          "description": "Tracked product URLs per tenant",
          "value": 50,
          "period": "per_month"
        }
      ],
      "pricing_rules": []
    }
  ]
}
```

- **Error handling**: domain exceptions propagate as 404/400 when the service cannot resolve a plan; ensure the integration layer maps them to your API contract if you customise the view.
- **Caching**: plans change infrequently; frontends can safely cache responses or leverage CDN caching with periodic invalidation driven by the admin CRUD workflows.

## Testing

Tests live under `core/pricing/tests/` and cover:
- Domain behaviour (`test_domain.py`).
- Service defaults and persistence interaction (`test_services.py`).
- Serializer output (`test_api.py`).
Run with:

```bash
python3.9 -m pytest core/pricing/tests
```

## Integration Notes

- The app is registered in `config/settings.py` inside `SHARED_APPS` so it is available across schemas.
- Admin registration happens in `PricingConfig.ready()` via `register_admin(default_admin_site)`.
- Future quota/usage modules should integrate through service interfaces to avoid cross-layer leakage.
