# API Authentication Implementation - Complete

## Summary

Implemented token-based authentication for Crawl Service API endpoints to secure bot access.

## Changes Made

### 1. Authentication Module (`services/crawl_service/api/auth.py`)
**Created new file** with authentication helper:
- `authenticate_bot(bot_id, api_token)` - Validates credentials against BotConfig
- Returns tuple: (is_authenticated: bool, result: BotConfig or error_dict)
- Checks:
  - Bot exists
  - Bot is enabled
  - API token matches

### 2. API Serializers (`services/crawl_service/api/serializers.py`)
**Updated**: Added `api_token` field (required) to:
- `BotPullRequestSerializer` - Pull endpoint
- `CrawlResultSubmissionSerializer` - Submit endpoint

### 3. API Views (`services/crawl_service/api/views.py`)
**Updated both endpoints**:

**Pull Endpoint** (`/api/crawl/pull/`):
- Added authentication check before processing
- Respects `bot_config.max_jobs_per_pull` limit
- Increments `bot_config.total_jobs_pulled`
- Returns 401/403 on auth failure

**Submit Endpoint** (`/api/crawl/submit/`):
- Added authentication check before processing
- Updates `bot_config.total_jobs_completed` on success
- Updates `bot_config.total_jobs_failed` on failure
- Returns 401/403 on auth failure

### 4. Admin Interface (`services/crawl_service/admin/admin.py`)
**Updated BotConfigAdmin**:
- Added `token_preview()` - Shows truncated token in list view
- Added `token_display()` - Shows full token with copy button in detail view
- Added `regenerate_token()` action - Regenerates API token
- Updated fieldsets to show token_display instead of raw api_token field

### 5. Documentation (`services/crawl_service/BOT_DEVELOPER_GUIDE.md`)
**Updated comprehensive guide**:
- Added authentication requirements section
- Updated Quick Start with token retrieval steps
- Updated all API endpoint documentation
- Updated code examples (Example 1 & 2)
- Added authentication troubleshooting section

## Authentication Flow

```
Bot Request
    ↓
Serializer validates (bot_id + api_token present)
    ↓
authenticate_bot(bot_id, api_token)
    ↓
Query BotConfig.objects.get(bot_id=bot_id)
    ↓
Check enabled=True
    ↓
Verify api_token matches
    ↓
Return BotConfig instance
    ↓
View processes request with bot_config
```

## Error Responses

### 401 Unauthorized
- Missing bot_id or api_token
- Bot not found
- Invalid api_token
- Bot has no token configured

### 403 Forbidden
- Bot is disabled (`enabled=False`)

## Admin Features

### Token Display
- **List View**: Shows first 20 chars of token
- **Detail View**: 
  - Full token in copyable format
  - "Copy Token" button (JavaScript clipboard API)
  - Instructions for regeneration

### Token Management
- **Action**: "🔄 Regenerate API Token"
- Generates new token format: `bot_<bot_id>_<32-char-random>`
- Invalidates old token immediately
- Shows warning message to update bots

## Token Format

```
bot_<bot_id>_<urlsafe_base64_32_chars>
```

Example:
```
bot_bot-001_Xk5m_lJ9k8NqR2vP3dT6yL8hW4jK5nM7
```

## Bot Statistics Tracking

Now automatically tracks per bot:
- `total_jobs_pulled` - Incremented on pull
- `total_jobs_completed` - Incremented on success submit
- `total_jobs_failed` - Incremented on failure submit
- `last_pull_at` - Timestamp of last pull
- `last_submit_at` - Timestamp of last submit

## Usage Example

### Environment Setup
```bash
export BOT_API_TOKEN="bot_bot-001_Xk5m_lJ9k8N..."
```

### Pull Request
```python
import requests
import os

resp = requests.post(
    'http://localhost:8000/api/crawl/pull/',
    json={
        'bot_id': 'bot-001',
        'api_token': os.environ['BOT_API_TOKEN'],
        'max_jobs': 5
    }
)
```

### Submit Request
```python
resp = requests.post(
    'http://localhost:8000/api/crawl/submit/',
    json={
        'bot_id': 'bot-001',
        'api_token': os.environ['BOT_API_TOKEN'],
        'job_id': job_id,
        'success': True,
        'price': 99.99,
        'currency': 'USD'
    }
)
```

## Testing Results

✅ Authentication module imports successfully  
✅ Serializers have api_token as required field  
✅ Admin display methods work without errors  
✅ Token verification works correctly:
- Valid token: authenticated ✓
- Invalid token: rejected ✗
- Missing token: rejected ✗
- Disabled bot: rejected ✗

## Migration Status

⚠️ **Note**: No database migration needed since `api_token` field already exists in BotConfig model. Existing bots may need tokens set manually in admin or will auto-generate on next save.

## Files Modified

1. ✅ `services/crawl_service/api/auth.py` (NEW)
2. ✅ `services/crawl_service/api/serializers.py`
3. ✅ `services/crawl_service/api/views.py`
4. ✅ `services/crawl_service/admin/admin.py`
5. ✅ `services/crawl_service/BOT_DEVELOPER_GUIDE.md`

## Next Steps (Optional)

1. **Rate Limiting**: Implement per-bot rate limiting using `bot_config.rate_limit_per_minute`
2. **Domain Filtering**: Enforce `bot_config.allowed_domains` restriction
3. **Token Rotation**: Schedule automatic token rotation policy
4. **Audit Logging**: Log all authentication attempts
5. **Token Expiry**: Add expiration dates to tokens

## Security Considerations

✅ Tokens are long random strings (32 bytes = 256 bits)  
✅ Tokens stored in database (not hashed - consider hashing for production)  
✅ Tokens required for all API operations  
✅ Disabled bots immediately rejected  
✅ Invalid tokens logged as warnings  
✅ Admin can regenerate tokens instantly  

**Recommendation**: Consider hashing tokens in database and passing plain token only once to bot on creation/regeneration.

---

**Implementation Date**: 2026-01-07  
**Status**: ✅ Complete and Tested  
**Breaking Change**: Yes - all bots must now provide `api_token` in requests
