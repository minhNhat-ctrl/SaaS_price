# Notification Module

Centralized notification management system for sending emails, SMS, push notifications, and webhooks across the platform.

## ⚠️ CRITICAL: Responsibility Boundaries

### What Notification Module Does ✅
- **Stores templates**: CRUD in Django admin only
- **Stores senders**: CRUD in Django admin only (provider configs, credentials)
- **Renders templates**: Jinja2 syntax for dynamic content
- **Sends notifications**: Delegates to provider adapters
- **Logs send attempts**: Audit trail (for debugging, compliance)

### What Application Layer Does ✅ (once created)
- **Decides to send**: "Signup complete? Send welcome email"
- **Chooses template**: "welcome_email_en" (with language support)
- **Sets context**: { user_name, activation_url, ... }
- **Calls notification.send(SendCommand)**

### What API Layer Does NOT Expose ❌
- **NO CRUD for templates**: Only Django admin manages
- **NO CRUD for senders**: Only Django admin manages
- **NO direct send endpoint**: Only application layer can trigger sends
- **Read-only logs**: API can view send history for dashboards

## Architecture Overview

The Notification module follows **Domain-Driven Design (DDD)** with strict layering:

```
api/ (minimal: read-only logs + internal send endpoint)
  ↓
services/ (use-cases: core send logic)
  ↓
repositories/ (data access interfaces & implementations)
  ↓
domain/ (entities, value objects, exceptions)
  ↓
infrastructure/ (Django ORM models, admin)
```

## API Endpoints (Minimal)

### Read-Only Log Endpoints
```
GET /api/notifications/logs/
  - Query filters: template_key, channel, status, recipient
  - Returns: paginated list of send attempts

GET /api/notifications/logs/{id}/
  - Returns: full log detail with context snapshot
```

### Internal Send Endpoint (Application Layer Only)
```
POST /api/notifications/send/
  - INTERNAL USE ONLY (called by application layer)
  - NOT exposed to external clients
  
Request:
{
  "template_key": "welcome_email",
  "channel": "EMAIL",
  "recipient": "user@example.com",
  "language": "en",
  "context": {
    "user_name": "Alice",
    "activation_url": "https://..."
  },
  "sender_key": "sendgrid_primary"  // optional, uses default if omitted
}

Response:
{
  "success": true,
  "message": "Notification sent successfully",
  "log_id": "uuid",
  "external_id": "sendgrid_message_id"
}
```

**NOTE**: This endpoint will be called exclusively by the Application layer once it's created.

## Data Model
    updated_at: datetime,
}
```

**Indexes**:
- `(channel, -is_active)` - Get active senders for a channel
- `(provider)` - Find all senders for a provider
- `(is_default, channel)` - Get default sender per channel

#### 2. NotificationTemplate
Stores reusable templates with Jinja2 support.

```python
{
    id: UUID,
    template_key: str,            # Unique identifier (e.g., "welcome_email", "payment_receipt")
    channel: Channel,             # EMAIL, SMS, PUSH, WEBHOOK
    language: str,                # en, vi, zh, etc.
    subject: str,                 # Email subject or notification title (Jinja2)
    body: str,                    # Email body or message content (Jinja2)
    is_active: bool,
    description: str,             # Internal notes
    created_at: datetime,
    updated_at: datetime,
}
```

**Unique Constraint**: `(template_key, channel, language)` - One template per key/channel/language combo

**Indexes**:
- `(template_key, channel)` - Fetch all language variants
- `(language, -is_active)` - List templates by language
- `(channel)` - List templates for a channel

#### 3. NotificationLog
Immutable audit trail of all send attempts.

```python
{
    id: UUID,
    template_key: str,
    channel: Channel,
    recipient: str,               # Email, phone, device token, or webhook URL
    status: SendStatus,           # PENDING, SENT, FAILED, BOUNCED, UNSUBSCRIBED
    error_message: str,           # If status is FAILED
    external_id: str,             # Provider's message ID for tracking
    context_snapshot: dict,       # Template variables used for rendering
    sender_key: str,              # Which sender was used
    sent_at: datetime,            # When successfully sent
    created_at: datetime,         # When log was created
}
```

**Indexes**:
- `(template_key, channel, -created_at)` - Recent sends for a template
- `(status, -created_at)` - Filter by status
- `(recipient, -created_at)` - Track sends to a recipient
- `(external_id)` - Lookup by provider ID

## Domain Entities

### SendCommand (Value Object)
Command pattern for instructing notification module to send.

```python
from core.notification.domain.value_objects import SendCommand, Channel

command = SendCommand(
    template_key='welcome_email',
    channel=Channel.EMAIL,
    recipient='user@example.com',
    language='en',                  # optional, defaults to 'en'
    context={                       # Jinja2 template variables
        'user_name': 'Alice',
        'activation_url': 'https://...',
        'company_name': 'ACME',
    },
    sender_key='sendgrid_primary'   # optional, uses default if not specified
)
```

### NotificationService (Application Service)

```python
from core.notification.services.use_cases import NotificationService
from core.notification.repositories.implementations import (
    DjangoNotificationSenderRepository,
    DjangoNotificationTemplateRepository,
    DjangoNotificationLogRepository,
)

service = NotificationService(
    sender_repo=DjangoNotificationSenderRepository(),
    template_repo=DjangoNotificationTemplateRepository(),
    log_repo=DjangoNotificationLogRepository(),
)

# Send notification
try:
    log = service.send(command)
    print(f"Sent! Log ID: {log.id}, External ID: {log.external_id}")
except TemplateNotFoundError:
    print("Template not found")
except SenderNotFoundError:
    print("Sender not configured")
except NotificationSendError as e:
    print(f"Send failed: {e}")
```

## Usage from Application Layer

**DO NOT** call the notification service directly from API views. Use the Application layer to orchestrate:

```python
# ❌ WRONG: Direct API call to notification service
def send_welcome_email_view(request):
    service = NotificationService(...)
    service.send(command)

# ✅ CORRECT: Application layer decides when/what to send
def send_welcome_email_view(request):
    from application.services import user_service  # Application layer
    user_service.send_welcome_email(request.user)  # Application decides
```

## Admin Interface

### NotificationSender Admin
Manage notification providers (email, SMS, webhook gateways).

- **List View**: sender_key, channel, provider, status, from_email, updated_at
- **Change View**: Edit credentials, toggle active/default status
- **Permissions**: Read-only for most fields; editable for is_active, is_default, credentials
- **Filters**: By channel, provider, active status

### NotificationTemplate Admin
Create and manage notification templates.

- **List View**: template_key, channel, language, active status, updated_at
- **Change View**: Edit subject & body (Jinja2 syntax supported)
- **Permissions**: Full CRUD
- **Filters**: By channel, language, active status

### NotificationLog Admin
Audit trail for all send attempts (read-only).

- **List View**: template_key, channel, recipient (truncated), status, sent_at, created_at
- **Detail View**: Full context, error messages, external provider ID
- **Permissions**: Read-only (audit trail cannot be modified or deleted)
- **Filters**: By channel, status, date range

## Admin Interface

### NotificationSender Admin ✏️ CRUD
Manage notification providers (email, SMS, webhook gateways).

- **List View**: sender_key, channel, provider, status, from_email, updated_at
- **Change View**: Edit credentials, toggle active/default status
- **Permissions**: Full CRUD (only via Django admin)
- **Filters**: By channel, provider, active status

### NotificationTemplate Admin ✏️ CRUD
Create and manage notification templates.

- **List View**: template_key, channel, language, active status, updated_at
- **Change View**: Edit subject & body (Jinja2 syntax supported)
- **Permissions**: Full CRUD (only via Django admin)
- **Filters**: By channel, language, active status

### NotificationLog Admin 🔍 Read-Only
Audit trail for all send attempts (immutable).

- **List View**: template_key, channel, recipient (truncated), status, sent_at, created_at
- **Detail View**: Full context, error messages, external provider ID
- **Permissions**: Read-only (audit trail cannot be modified or deleted)
- **Filters**: By channel, status, date range
    "context": {
        "user_name": "Alice",
        "activation_url": "https://..."
    },
    "sender_key": "sendgrid_primary"
}
```

Response:
```json
{
    "success": true,
    "message": "Notification sent successfully",
    "log_id": "uuid-123",
    "external_id": "sendgrid-message-id-456"
}
```

## Jinja2 Template Rendering

Templates support full Jinja2 syntax:

```
Subject: Welcome {{ user_name }}!

Body:
Hello {{ user_name }},

Welcome to {{ company_name }}! 

To activate your account, click here:
{{ activation_url }}

{% if is_premium %}
As a premium member, you get access to advanced features!
{% endif %}

Best regards,
The {{ company_name }} Team
```

Template variables are passed via `context` in `SendCommand`:

```python
context = {
    'user_name': 'Alice',
    'company_name': 'ACME',
    'activation_url': 'https://...',
    'is_premium': True,
}
```

## Exception Handling

```python
from core.notification.domain.exceptions import (
    TemplateNotFoundError,
    SenderNotFoundError,
    TemplateRenderError,
    NotificationSendError,
    InvalidTemplateKeyError,
)

try:
    service.send(command)
except TemplateNotFoundError:
    # Handle missing template
except SenderNotFoundError:
    # Handle missing sender/provider
except TemplateRenderError:
    # Handle Jinja2 rendering issues
except NotificationSendError:
    # Handle provider errors (API failure, invalid recipient, etc.)
```

## Multi-Tenancy

Notification module is **shared** (not per-tenant):

- Senders and templates are managed globally
- Logs are stored globally but can be filtered by template/recipient
- Application layer can pass tenant context via template variables

Example:
```python
SendCommand(
    template_key='welcome_email',
    channel=Channel.EMAIL,
    recipient=user.email,
    context={
        'user_name': user.name,
        'tenant_name': user.tenant.name,  # Tenant-specific context
        'logo_url': user.tenant.logo_url,
    }
)
```

## Integration Checklist

- [ ] Add NotificationSender configurations (email provider, SMS gateway, etc.) via admin
- [ ] Create templates via admin (at least one per channel/language)
- [ ] Create Application use-cases that call notification.send(command)
- [ ] Update API views to route through Application layer
- [ ] Implement provider adapters (SendGrid, Twilio, Firebase, etc.)
- [ ] Add Celery tasks for async sending (optional)
- [ ] Monitor notification logs for failures

## Future Enhancements

1. **Provider Adapters**: Implement SendGridAdapter, TwilioAdapter, FirebaseAdapter, WebhookAdapter
2. **Async Processing**: Celery integration for non-blocking sends
3. **Retry Logic**: Automatic retry for failed sends
4. **Unsubscribe Management**: Track and respect user preferences
5. **Template Versioning**: Track template changes over time
6. **A/B Testing**: Test multiple subject lines or message variants
7. **Scheduling**: Delay sends or schedule for specific times
8. **Rate Limiting**: Prevent notification spam

## Files

```
core/notification/
├── domain/
│   ├── __init__.py          # Exports entities, value objects, exceptions
│   ├── entities.py          # NotificationSender, NotificationTemplate, NotificationLog
│   ├── value_objects.py     # Channel, SendStatus, SendCommand
│   └── exceptions.py        # 5 domain exceptions
├── repositories/
│   ├── __init__.py          # Repository interfaces
│   └── implementations.py    # Django ORM implementations
├── infrastructure/
│   ├── __init__.py
│   ├── django_models.py     # 3 ORM models with indexes
│   └── django_admin.py      # Admin classes (read-only/editable)
├── services/
│   ├── __init__.py
│   └── use_cases.py         # NotificationService.send(command)
├── api/
│   ├── __init__.py
│   ├── serializers.py       # DRF serializers
│   ├── views.py             # ViewSets & SendNotificationView
│   └── urls.py              # API URL routing
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py      # Create 3 tables with indexes
├── tests.py                 # Basic domain tests
└── apps.py                  # App configuration
```
