# Application Layer

Central orchestration layer that coordinates cross-module workflows for the SaaS platform.

## Objectives

1. **Single entry point** for all frontend and external requests.
2. **Orchestrate module services** via explicit use-case classes.
3. **Enforce business rules** that span multiple bounded contexts (modules).
4. **Provide stable APIs** to external clients while allowing internal module refactors.
5. **Isolate infrastructure** (Django/DRF) from business orchestration logic.

## Layered Flow

```
HTTP Request → application.interfaces (adapters)
             → application.use_cases (orchestration)
             → core.<module>.services.use_cases (module application services)
             → core.<module>.repositories / domain
```

## Directory Structure

```
application/
├── __init__.py
├── README.md
├── dto/                # Shared DTOs used across use cases
│   ├── __init__.py
│   └── base.py
├── interfaces/         # Adapters exposing use cases (HTTP, CLI, etc.)
│   ├── __init__.py
│   └── api.py
├── orchestrators/      # Composite workflows spanning multiple use cases
│   ├── __init__.py
│   └── base.py
├── tests/
│   └── __init__.py
└── use_cases/          # Application-level use cases
    ├── __init__.py
    └── base.py
```

### Upcoming Sub-packages

Each business domain will register its entry-point use cases under dedicated subpackages:

```
application/use_cases/
├── billing/
├── notification/
├── onboarding/
├── subscription/
└── support/
```

Orchestrators will compose multiple use cases for long-running workflows (sagas):

```
application/orchestrators/
└── tenant_onboarding.py  # Example saga orchestrating identity, tenants, billing, notification
```

## Dependency Rules

- `application` may depend on module services and DTOs.
- Module services **must not** import `application`.
- Interfaces (HTTP, CLI, Jobs) depend on `application` only, never on module services directly.
- Application layer delivers sanitized DTOs to interfaces; raw domain objects stay inside modules.

## Responsibilities

| Layer            | Responsibilities                                                   |
|------------------|--------------------------------------------------------------------|
| `interfaces`     | Validate input, map transport concerns → application DTOs          |
| `use_cases`      | Orchestrate business logic, call module use cases, manage retries  |
| `orchestrators`  | Coordinate multi-step workflows, handle compensations/failures     |
| `dto`            | Typed payloads shared between adapters and use cases               |

## Example Flow (Planned)

1. **User signup request** hits `/api/signup/`.
2. DRF view delegates to `application.interfaces.api.SignupEndpoint`.
3. Adapter validates request, builds DTO, calls `OnboardTenantUseCase.execute()`.
4. Use case:
   - Creates identity via `core.identity.services.use_cases.CreateUserUseCase`.
   - Provisions tenant via `core.tenants.services.use_cases.CreateTenantUseCase`.
   - Assigns default plan via `core.subscription.services.use_cases.AssignPlanUseCase`.
   - Sends welcome notification via `core.notification.services.use_cases.NotificationService`.
5. Aggregates results into `UseCaseResult`, returns to adapter.
6. Adapter formats API response.

## Implementation Roadmap

1. **Identify module use cases**: ensure each module exposes `services/use_cases.py` with callable classes.
2. **Map application workflows**: list cross-module processes (signup, billing events, quotas, notifications).
3. **Create application use case classes** in `application/use_cases/<domain>/`.
4. **Introduce orchestrators** for complex workflows (e.g., tenant onboarding saga).
5. **Refactor API views** to instantiate `ApplicationAPIView` adapters and route through use cases.
6. **Add tests** covering orchestration logic (unit + integration via mocked module services).

## Next Actions

- [ ] Document module-specific use-case contracts.
- [ ] Scaffold onboarding use case (`application/use_cases/onboarding/tenant_signup.py`).
- [ ] Scaffold billing sync use case (bridge payment events to notification + subscription updates).
- [ ] Build API adapter mapping (DRF views → ApplicationAPIView).
- [ ] Update project README to reflect new flow (API → application → module).
