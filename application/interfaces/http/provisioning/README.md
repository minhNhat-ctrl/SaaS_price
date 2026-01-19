# Provisioning Flow HTTP API

## Overview

Provisioning là luồng onboarding chính của PriceSynC. HTTP API này expose luồng đó cho React SPA frontend.

**Endpoint**: `POST /api/provisioning/signup/`

## Architecture

```
Request (JSON)
    ↓
SignupRequestSerializer
    ↓ to_command()
SignupCommand (DTO)
    ↓
ProvisioningSignupView.post()
    ↓
ProvisioningFlowOrchestrator.run()
    ├─ Step 1: Signup (via signup_handler)
    ├─ Step 2: Verify Email (via verify_handler)
    ├─ Step 3: Signin (via signin_handler)
    ├─ Step 4: Create Tenant (via create_tenant_handler)
    ├─ Step 5: Resolve Subscription (via resolve_subscription_handler)
    ├─ Step 6: Assign Plan (via assign_plan_handler)
    ├─ Step 7: Quote Payment (via quote_handler + charge_handler)
    └─ Step 8: Activate Tenant (via activate_handler)
    ↓
ProvisioningContext
    ↓
ProvisioningContextResponseSerializer
    ↓ from_context()
Response (JSON)
```

## Request/Response

### Request

```http
POST /api/provisioning/signup/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123",
  "source": "web"
}
```

### Response (201 Created)

```json
{
  "success": true,
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "tenant_id": "660e8400-e29b-41d4-a716-446655440000",
    "plan_code": "starter",
    "subscription_status": "trial",
    "requires_payment": false,
    "metadata": {
      "verify_required": "true",
      "email_verified": "true",
      "session_id": "sess_123456",
      "tenant_status": "created",
      "trial_days": "14",
      "requires_payment": "false",
      "activation_status": "active"
    }
  },
  "error": null,
  "message": "Provisioning completed successfully"
}
```

### Response (Error 400)

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "detail": {
      "email": ["Enter a valid email address."],
      "password": ["Ensure this field has at least 8 characters."]
    }
  },
  "message": "Validation failed"
}
```

## File Structure

```
provisioning/
├── __init__.py
├── serializers.py          # SignupRequestSerializer, ProvisioningContextResponseSerializer
├── views.py                # ProvisioningSignupView, ProvisioningStatusView
├── urls.py                 # URL routing
├── providers.py            # Orchestrator factory & DI
├── README.md              # This file
└── IMPLEMENTATION_GUIDE.md # Detailed implementation guide
```

## Step-by-Step Handlers

Each step is handled by an injected handler function:

| Step | Input | Output | Handler Type |
|------|-------|--------|--------------|
| Signup | `SignupCommand` | `SignupResult` | `SignupHandler` |
| Verify Email | `ProvisioningContext` | `VerifyEmailResult` | `VerifyHandler` |
| Signin | `ProvisioningContext` | `SigninResult` | `SigninHandler` |
| Create Tenant | `ProvisioningContext` | `CreateTenantResult` | `CreateTenantHandler` |
| Resolve Subscription | `ProvisioningContext` | `ResolveSubscriptionResult` | `ResolveSubscriptionHandler` |
| Assign Plan | `ProvisioningContext` | `AssignPlanResult` | `AssignPlanHandler` |
| Quote Payment | `ProvisioningContext` | `CreateQuoteResult` | `QuoteHandler` |
| Charge Payment | `ProvisioningContext` | `ChargePaymentResult` | `ChargeHandler` |
| Activate Tenant | `ProvisioningContext` | `ActivateTenantResult` | `ActivateHandler` |

## Toggle Management

Each step can be independently enabled/disabled via Django Admin:

**Admin URL**: `/admin/application/flowruletoggle/`

Toggles:
- `provisioning.signup` (default: enabled)
- `provisioning.verify_email` (default: enabled)
- `provisioning.signin` (default: enabled)
- `provisioning.create_tenant` (default: enabled)
- `provisioning.resolve_subscription` (default: enabled)
- `provisioning.assign_plan` (default: enabled)
- `provisioning.quote_payment` (default: enabled)
- `provisioning.activate_tenant` (default: enabled)

If a step is disabled:
- The step will be skipped
- Context will still be propagated to next step
- Subsequent steps will execute normally

This allows gradual rollout or testing without full flow disruption.

## Handler Injection

Handlers are injected via `ProvisioningOrchestratorProvider`:

```python
from .providers import ProvisioningOrchestratorProvider, set_provisioning_orchestrator_provider

provider = ProvisioningOrchestratorProvider(
    toggle_service=FlowToggleService(),
    signup_handler=get_signup_handler(),
    verify_handler=get_verify_handler(),
    # ... other handlers
)
set_provisioning_orchestrator_provider(provider)
```

Recommended injection point: `application/apps.py` in `ready()` method.

## Handler Examples

### Signup Handler

```python
from application.dto.provisioning import SignupCommand, SignupResult

def get_signup_handler():
    service = get_identity_service()
    
    def handler(cmd: SignupCommand) -> SignupResult:
        user = service.create_user(
            email=cmd.email,
            password=cmd.password,
            source=cmd.source
        )
        return SignupResult(
            user_id=user.id,
            verify_required=True
        )
    
    return handler
```

### Create Tenant Handler

```python
from application.dto.provisioning import CreateTenantResult

def get_create_tenant_handler():
    service = get_tenants_service()
    
    def handler(ctx: ProvisioningContext) -> CreateTenantResult:
        tenant = service.create_tenant(
            owner_id=ctx.user_id,
            name=f"{ctx.user_id}'s workspace"
        )
        return CreateTenantResult(
            tenant_id=tenant.id,
            status="created"
        )
    
    return handler
```

## Error Handling

The view catches all exceptions and returns standard error response:

```python
try:
    context = orchestrator.run(command)
    # ... return success response
except Exception as exc:
    return Response(
        {
            'success': False,
            'data': None,
            'error': {
                'code': exc.__class__.__name__,
                'detail': str(exc),
            },
            'message': f'Provisioning failed: {str(exc)}',
        },
        status=400,
    )
```

Domain exceptions should map to appropriate HTTP status:
- `DomainValidationError` → 400 Bad Request
- `ResourceNotFoundError` → 404 Not Found
- `UnauthorizedError` → 401 Unauthorized
- `ConflictError` → 409 Conflict
- Default → 400 Bad Request

## Testing

### Manual Test (curl)

```bash
curl -X POST http://localhost:8000/api/provisioning/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepassword123",
    "source": "web"
  }'
```

### Unit Tests

```python
from django.test import TestCase
from application.dto.provisioning import SignupCommand
from .serializers import SignupRequestSerializer

class SignupSerializerTest(TestCase):
    def test_valid_request(self):
        data = {
            'email': 'test@example.com',
            'password': 'securepassword123',
            'source': 'web'
        }
        serializer = SignupRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        cmd = serializer.to_command()
        self.assertEqual(cmd.email, 'test@example.com')
        self.assertEqual(cmd.password, 'securepassword123')
```

### Integration Tests

```python
from django.test import APITestCase
from unittest.mock import patch, MagicMock

class ProvisioningSignupAPITest(APITestCase):
    @patch('handlers')
    def test_successful_signup(self, mock_handlers):
        # Mock handlers
        mock_handlers.signup.return_value = SignupResult(user_id='123', verify_required=True)
        
        # Test API
        response = self.client.post(
            '/api/provisioning/signup/',
            {
                'email': 'test@example.com',
                'password': 'securepassword123'
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['success'], True)
        self.assertEqual(response.json()['data']['user_id'], '123')
```

## Next Steps

1. Implement handlers in each core module
2. Wire handlers in `application/apps.py`
3. Register provisioning URLs in `config/urls.py`
4. Create and run tests
5. Deploy and monitor

See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) for detailed instructions.
