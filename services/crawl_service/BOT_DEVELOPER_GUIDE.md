# Bot Developer Guide - Crawl Service API

Comprehensive guide for building bots that integrate with the Crawl Service to execute web scraping tasks.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Quick Start](#quick-start)
3. [API Endpoints](#api-endpoints)
4. [State Machine](#state-machine)
5. [Error Handling](#error-handling)
6. [Concurrency & Locking](#concurrency--locking)
7. [Retry Logic](#retry-logic)
8. [Best Practices](#best-practices)
9. [Examples](#examples)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Pull-Based Bot Architecture (Domain-Grouped Policies)

The Crawl Service uses a **pull-based** architecture with **domain-grouped policies** for scalability to millions of URLs:

```
┌─────────────────────────────────────────────────────────────┐
│ Crawl Service (Django backend)                              │
│  - CrawlPolicy: Domain-based group (1 policy = many URLs)   │
│  - CrawlJob: Individual execution via ProductURL hash       │
│  - CrawlResult: Bot-submitted outcomes                     │
└─────────────────────────────────────────────────────────────┘
         ▲                                    │
         │ 1. Pull request                   │
         │ 2. Lock acquired                  │
         │                                   │ 3. Result submit
         │                                   │ 4. State transition
         │                                   │
         └───────────────────────────────────┘
           Bot 1, Bot 2, ..., Bot N (Independent workers)
```

### CrawlPolicy Design (Domain-Based Grouping)

**Old Design (Per-URL):**
- ❌ 1 CrawlPolicy per URL
- ❌ Not scalable for millions of URLs
- ❌ Wasteful: 2048 char URL per job record

**New Design (Domain-Based):**
- ✅ 1 CrawlPolicy per domain/pattern (e.g., "amazon.co.jp - Default")
- ✅ Pattern matching for selective crawling
- ✅ Scales to millions of URLs
- ✅ Optimized: 64-char hash references instead of full URLs

Example:
```python
policy = CrawlPolicy.objects.create(
    domain=Domain.objects.get(name='amazon.co.jp'),
    name='Default Policy',
    url_pattern='',  # Empty = match all URLs
    frequency_hours=24,
    priority=5,
    enabled=True
)

# This 1 policy manages ALL URLs for amazon.co.jp
# Jobs reference ProductURL via hash: product_url_hash (64 chars vs 2048)
```

### State Machine: Job Lifecycle (5 States)

Every crawl job follows a deterministic state machine with **5 states**:

| State | Value | Description | Bot Action |
|-------|-------|-------------|------------|
| **PENDING** | `pending` | Ready to be pulled by a bot | Pull job |
| **LOCKED** | `locked` | Bot is executing, lock held | Execute + Submit |
| **DONE** | `done` | Crawl succeeded, result saved | None (terminal) |
| **FAILED** | `failed` | Crawl failed, retries exhausted | None (terminal) |
| **EXPIRED** | `expired` | Lock TTL exceeded, bot didn't respond | Admin recovery |

```
                              ┌─────────────────────────┐
                              │         PENDING         │
                              │  (ready to crawl)       │
                              └───────────┬─────────────┘
                                          │
                                          │ POST /api/crawl/pull/
                                          │ bot acquires lock
                                          ▼
                              ┌─────────────────────────┐
                              │         LOCKED          │
                              │  (bot executing)        │
                              │  TTL: 600s default      │
                              └─────┬───────────┬───────┘
                                    │           │
            ┌───────────────────────┤           ├───────────────────────┐
            │                       │           │                       │
            │ TTL exceeded          │           │                       │
            │ (no submit)           │           │                       │
            ▼                       │           │                       ▼
┌─────────────────────┐             │           │             ┌─────────────────────┐
│       EXPIRED       │             │           │             │        DONE         │
│  (lock timeout)     │             │           │             │  (crawl succeeded)  │
│  Admin can reset    │             │           │             │  Result saved       │
└─────────────────────┘             │           │             │  Policy rescheduled │
                                    │           │             └─────────────────────┘
                                    │           │
                POST /api/crawl/submit/         POST /api/crawl/submit/
                success=false                   success=true
                                    │           │
                                    ▼           │
                    ┌───────────────────────┐   │
                    │   retry_count check   │   │
                    └───────┬───────┬───────┘   │
                            │       │           │
          retry_count       │       │  retry_count >= max_retries - 1
          < max_retries - 1 │       │
                            ▼       ▼
                  ┌───────────┐   ┌─────────────────────┐
                  │  PENDING  │   │       FAILED        │
                  │  (retry)  │   │  (permanent fail)   │
                  └───────────┘   │  Policy rescheduled │
                                  │  with backoff       │
                                  └─────────────────────┘
```

### Key Concepts

| Term | Meaning |
|------|---------|
| **CrawlPolicy** | Defines when/how a URL should be crawled (frequency, retry config, timeout) |
| **CrawlJob** | Individual execution instance with state tracking and locking |
| **Lock** | Prevents concurrent execution by same URL (holds `locked_by`, `locked_at`, TTL) |
| **TTL** | Time-To-Live: job lock expires if bot doesn't respond within this period |
| **Retry** | Auto-transitioned back to PENDING if crawl fails but retries remain |
| **CrawlResult** | Bot-submitted outcome (price, stock status, parsed data) |

---

## Quick Start

### 1. Get API Token

1. Go to Django Admin: `/admin/secure-admin-2025/`
2. Navigate to **Bot Configuration**
3. Click on your bot or create a new one
4. Copy the **API Token** field
5. Use this token in all API requests

### 2. Authenticate (Required)

All API endpoints require authentication using:
- `bot_id`: Your bot identifier from BotConfig
- `api_token`: Your unique API token

Token format: `bot_<bot_id>_<random_string>`

Example: `bot_bot-001_Xk5m_lJ9k8N...`

### 3. Bot Pulls a Job

```bash
curl -X POST http://127.0.0.1:8005/api/crawl/pull/ \
  -H "Content-Type: application/json" \
  -d '{
    "bot_id": "bot-001",
    "api_token": "bot_bot-001_Xk5m_lJ9k8N...",
    "max_jobs": 5,
    "domain": "example.com"
  }'
```

Response:
```json
{
  "success": true,
  "data": {
    "jobs": [
      {
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "url": "https://example.com/product/123",
        "priority": 10,
        "max_retries": 3,
        "timeout_seconds": 600,
        "retry_count": 0,
        "locked_until": "2025-01-07T07:20:00Z"
      }
    ],
    "count": 1,
    "skipped": 2  # Already locked by other bots
  }
}
```

### 4. Bot Executes the Job

Bot now has 10 minutes (600s) to:
- Fetch the URL
- Extract data (price, stock, etc.)
- Parse the HTML/JSON
- Submit the result

### 5. Bot Submits Result

```bash
curl -X POST http://localhost:8005/api/crawl/submit/ \
  -H "Content-Type: application/json" \
  -d '{
    "bot_id": "bot-001",
    "api_token": "bot_bot-001_Xk5m_lJ9k8N...",
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "success": true,
    "price": 99.99,
    "currency": "USD",
    "title": "Amazing Product",
    "in_stock": true,
    "parsed_data": {
      "sku": "ABC123",
      "rating": 4.5
    },
    "raw_html": "<html>...</html>"
  }'
```

Response:
```json
{
  "success": true,
  "data": {
    "result_id": "550e8400-e29b-41d4-a716-446655440001",
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "done",
    "price": 99.99,
    "currency": "USD",
    "policy_next_run": "2025-01-08T06:54:00Z"
  }
}
```

---

## API Endpoints

### Authentication Required

All requests must include both credentials in the JSON body:

```json
{
  "bot_id": "string (required, max 100 chars)",
  "api_token": "string (required, from BotConfig)"
}
```

Authentication responses are uniform:

| Status | Error | Meaning |
|--------|-------|---------|
| 401 | `authentication_error` | Missing bot_id/api_token, invalid token, or bot not found |
| 403 | `authentication_error` | Bot exists but is disabled |

### POST /api/crawl/pull/

Bot requests available PENDING jobs and acquires locks atomically.

**Status codes**: `200 OK` on success, error codes below when applicable.

#### Request

```json
{
  "bot_id": "string (required, max 100 chars)",
  "api_token": "string (required)",
  "max_jobs": "integer (optional, default 10, capped by bot_config.max_jobs_per_pull, hard cap 100)",
  "domain": "string (optional, contains filter like 'example.com')"
}
```

#### Response (Success)

```json
{
  "success": true,
  "data": {
    "jobs": [
      {
        "job_id": "UUID",
        "url": "string",
        "priority": "integer (1-20)",
        "max_retries": "integer",
        "timeout_seconds": "integer (lock TTL seconds)",
        "retry_count": "integer (current retries)",
        "locked_until": "ISO 8601 datetime"
      }
    ],
    "count": "integer (assigned jobs)",
    "skipped": "integer (jobs already locked by other bots)"
  }
}
```

**Notes**:
- There is no `job_already_locked` error; contention is reported via `skipped`.
- Jobs are ordered by `priority DESC` then `created_at ASC`.

#### Errors

| Status | Error | Meaning |
|--------|-------|---------|
| 400 | `validation_error` | Invalid request data |
| 401 | `authentication_error` | Invalid credentials |
| 403 | `authentication_error` | Bot is disabled |
| 500 | `internal_error` | Server error |

---

### POST /api/crawl/submit/

Bot submits crawl result after executing job.

**Status codes**:
- `201 Created` when a success result is saved (success=true)
- `200 OK` when failure is accepted (auto-retry or retries exhausted)
- Error codes per table below

#### Request (Success Case)

```json
{
  "bot_id": "string (required)",
  "api_token": "string (required)",
  "job_id": "UUID (required)",
  "success": true,
  "price": "decimal (required, >= 0.00)",
  "currency": "string (required, 3-letter ISO like USD)",
  "title": "string (optional, product name)",
  "in_stock": "boolean (optional, default true)",
  "raw_html": "string (optional, for debugging)",
  "parsed_data": "object (optional, any custom data)"
}
```

#### SaaS Multi-Job Worker - parsed_data Structure

Khi sử dụng `saas_multi_job_worker`, bot sẽ tự động gửi `parsed_data` với cấu trúc sau:

```json
{
  "bot_id": "bot-001",
  "api_token": "abcd-128nkaj-321-21",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "success": true,
  "price": 1290000.0,
  "currency": "VND",
  "parsed_data": {
    "source_url": "https://example.com/product/123",
    "price_formatted": "1,290,000 VND",
    "price_sources": ["jsonld", "html_ml"],
    "confidence": 0.8504585067273558,
    "price_extraction": {
      "extract_price_from_jsonld": {
        "price": 1290000,
        "currency": "VND",
        "confidence": 0.95
      },
      "extract_price_from_og": {
        "price": null,
        "currency": null,
        "confidence": 0.0
      },
      "extract_price_from_microdata": {
        "price": null,
        "currency": null,
        "confidence": 0.0
      },
      "extract_price_from_script_data": {
        "price": 1290000,
        "currency": "VND",
        "confidence": 0.85
      },
      "extract_price_from_html_ml": {
        "price": 1290000,
        "currency": "VND",
        "confidence": 0.8504585067273558
      }
    }
  }
}
```

**parsed_data Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `source_url` | string | URL nguồn đã crawl |
| `price_formatted` | string | Giá đã format human-readable (e.g., "1,290,000 VND") |
| `price_sources` | array | Danh sách các nguồn đã extract được giá |
| `confidence` | float | Độ tin cậy tổng hợp (0.0 - 1.0) |
| `price_extraction` | object | Chi tiết extraction từ mỗi nguồn |

**price_extraction Sources:**

| Source | Description |
|--------|-------------|
| `extract_price_from_jsonld` | Giá từ JSON-LD structured data (highest priority) |
| `extract_price_from_og` | Giá từ Open Graph meta tags |
| `extract_price_from_microdata` | Giá từ HTML Microdata |
| `extract_price_from_script_data` | Giá từ inline JavaScript/JSON |
| `extract_price_from_html_ml` | Giá từ ML-based DOM extraction |

#### Request (Failure Case)

```json
{
  "bot_id": "string",
  "api_token": "string",
  "job_id": "UUID",
  "success": false,
  "error_msg": "string (optional, error description)"
}
```

#### Response (Success - Result Saved)

```json
{
  "success": true,
  "data": {
    "result_id": "UUID",
    "job_id": "UUID",
    "status": "done",
    "price": "decimal",
    "currency": "string",
    "policy_next_run": "ISO 8601 (next scheduled run, can be null)"
  }
}
```

#### Response (Failure - Auto Retry)

If `retry_count < max_retries - 1`, job transitions back to `pending` for retry:

```json
{
  "success": true,
  "data": {
    "job_id": "UUID",
    "status": "pending",
    "retry_count": 1,
    "max_retries": 3,
    "message": "Job marked for retry"
  }
}
```

#### Response (Failure - Retries Exhausted)

If retries are exhausted, job transitions to `failed`:

```json
{
  "success": true,
  "data": {
    "job_id": "UUID",
    "status": "failed",
    "retry_count": 3,
    "max_retries": 3,
    "error": "Timeout after 3 retries",
    "message": "Retries exhausted"
  }
}
```

#### Errors

| Status | Error | Meaning |
|--------|-------|---------|
| 400 | `validation_error` | Missing required fields (price, currency if success=true) |
| 400 | `authentication_error` | Missing or invalid credentials |
| 403 | `authentication_error` | Bot is disabled or unauthorized |
| 404 | `job_not_found` | Job ID doesn't exist |
| 400 | `job_not_locked` | Job is not in LOCKED state (can't submit) |
| 403 | `not_assigned` | Job locked by different bot |
| 400 | `lock_expired` | Lock TTL exceeded, job marked as EXPIRED |
| 500 | `internal_error` | Server error |

---

## State Machine

### All 5 States

| State | Constant | Description |
|-------|----------|-------------|
| PENDING | `CrawlJob.STATE_PENDING` | Job is waiting to be pulled by a bot |
| LOCKED | `CrawlJob.STATE_LOCKED` | Bot has acquired lock, currently executing |
| DONE | `CrawlJob.STATE_DONE` | Crawl succeeded, result saved (terminal) |
| FAILED | `CrawlJob.STATE_FAILED` | Crawl failed, retries exhausted (terminal) |
| EXPIRED | `CrawlJob.STATE_EXPIRED` | Lock TTL exceeded without response |

### State Transitions (Bot Perspective)

#### 1. PENDING → LOCKED (Bot pulls job)

**Trigger**: `POST /api/crawl/pull/`

**What happens**:
1. Bot sends pull request with `bot_id` + `api_token`
2. System finds PENDING jobs, orders by priority DESC
3. For each job, attempts to acquire lock via `job.lock_for_bot(bot_id)`
4. Lock acquired: `status='locked'`, `locked_by=bot_id`, `locked_at=now()`
5. Job returned to bot with `locked_until` timestamp

**Bot receives**:
```json
{
  "job_id": "uuid",
  "url": "https://...",
  "timeout_seconds": 600,
  "locked_until": "2026-01-07T10:10:00Z"
}
```

#### 2. LOCKED → DONE (Success submit)

**Trigger**: `POST /api/crawl/submit/` with `success=true`

**What happens**:
1. Bot sends result with price, currency, title, etc.
2. System verifies: job is LOCKED, locked_by matches bot_id, lock not expired
3. Creates `CrawlResult` record
4. Calls `job.mark_done()`: clears lock, sets status='done'
5. Reschedules policy: `policy.schedule_next_run(success=True)`

**Bot receives**:
```json
{
  "result_id": "uuid",
  "status": "done",
  "policy_next_run": "2026-01-08T10:00:00Z"
}
```

#### 3. LOCKED → PENDING (Failure with retries)

**Trigger**: `POST /api/crawl/submit/` with `success=false` and `retry_count < max_retries - 1`

**What happens**:
1. Bot sends failure with optional `error_msg`
2. System calls `job.mark_failed(error_msg, auto_retry=True)`
3. Increments `retry_count`, clears lock
4. Sets `status='pending'` for re-queue
5. Job can be pulled again by any bot

**Bot receives**:
```json
{
  "job_id": "uuid",
  "status": "pending",
  "retry_count": 1,
  "max_retries": 3,
  "message": "Job marked for retry"
}
```

#### 4. LOCKED → FAILED (Retries exhausted)

**Trigger**: `POST /api/crawl/submit/` with `success=false` and `retry_count >= max_retries - 1`

**What happens**:
1. Bot sends failure with optional `error_msg`
2. System calls `job.mark_failed(error_msg, auto_retry=False)`
3. Sets `status='failed'` (terminal state)
4. Reschedules policy with backoff: `policy.schedule_next_run(success=False)`

**Bot receives**:
```json
{
  "job_id": "uuid",
  "status": "failed",
  "retry_count": 3,
  "max_retries": 3,
  "message": "Retries exhausted"
}
```

#### 5. LOCKED → EXPIRED (Lock timeout)

**Trigger**: Lock TTL exceeded without submit (bot crashed, network issue)

**What happens**:
1. Bot doesn't call submit within `lock_ttl_seconds` (default 600s)
2. If bot tries to submit after TTL: `lock_expired` error returned
3. System calls `job.mark_expired()`: clears lock, sets status='expired'
4. Admin can manually reset to PENDING via Django Admin

**Bot receives** (if attempting late submit):
```json
{
  "success": false,
  "error": "lock_expired",
  "detail": "Lock TTL exceeded"
}
```

### State Transition Summary

| From | To | Trigger | Method Called |
|------|------|---------|---------------|
| PENDING | LOCKED | pull | `job.lock_for_bot(bot_id)` |
| LOCKED | DONE | submit success=true | `job.mark_done()` |
| LOCKED | PENDING | submit success=false (retries left) | `job.mark_failed(auto_retry=True)` |
| LOCKED | FAILED | submit success=false (no retries) | `job.mark_failed(auto_retry=False)` |
| LOCKED | EXPIRED | TTL exceeded | `job.mark_expired()` |

### Internal State Properties

```python
# State constants
CrawlJob.STATE_PENDING   # 'pending'
CrawlJob.STATE_LOCKED    # 'locked'
CrawlJob.STATE_DONE      # 'done'
CrawlJob.STATE_FAILED    # 'failed'
CrawlJob.STATE_EXPIRED   # 'expired'

# Job instance properties
job.status               # Current state string
job.locked_by            # Bot ID holding lock (if LOCKED)
job.locked_at            # When lock was acquired (datetime)
job.lock_ttl_seconds     # Lock duration (default 600)
job.retry_count          # Current retry attempts
job.max_retries          # Max allowed retries
job.last_error           # Last error message

# Job methods
job.is_lock_expired()    # True if LOCKED and TTL exceeded
job.can_retry()          # True if retry_count < max_retries
job.lock_for_bot(bot_id) # Attempt to acquire lock
job.mark_done()          # Transition to DONE
job.mark_failed(msg)     # Transition to FAILED/PENDING
job.mark_expired()       # Transition to EXPIRED
```

---

## Error Handling

### Validation Errors (400)

Caused by malformed requests:

```json
{
  "success": false,
  "error": "validation_error",
  "detail": {
    "bot_id": ["This field is required."],
    "price": ["Decimal value too large."]
  }
}
```

**Handle by**:
- Check required fields before sending
- Ensure `currency` is exactly 3 characters
- Ensure `price >= 0.00`
- Ensure `success` is boolean (true/false)

### Concurrency Errors (400, 403)

Job locked by another bot:

```json
{
  "success": false,
  "error": "not_assigned",
  "detail": "Job locked by bot-002, not bot-001"
}
```

**Handle by**:
- Only submit results for jobs you pulled
- Don't attempt to submit jobs pulled by other bots

Already locked (during pull):

```json
{
  "success": true,
  "data": {
    "jobs": [...],
    "count": 1,
    "skipped": 5  # These were already locked by other bots
  }
}
```

**Handle by**:
- Expect `skipped` to be non-zero in competitive environment
- Only process jobs returned in `jobs` array

### Lock Expiration (400)

```json
{
  "success": false,
  "error": "lock_expired",
  "detail": "Lock TTL exceeded"
}
```

**Handle by**:
- Complete crawl within `timeout_seconds` (default 600s)
- If expected to take longer, request fewer jobs per pull
- Consider network retry logic with timeouts

### Not Found (404)

```json
{
  "success": false,
  "error": "job_not_found",
  "detail": "Job 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Handle by**:
- Verify job_id is correct UUID format
- Don't attempt to submit for deleted/expired jobs
- Re-pull for fresh job list if needed

### Server Errors (500)

```json
{
  "success": false,
  "error": "internal_error",
  "detail": "Database connection error"
}
```

**Handle by**:
- Implement exponential backoff retry
- Log full error for debugging
- Report to admin if persistent

---

## Concurrency & Locking

### Lock Mechanism

When a bot successfully pulls a job:

```
Job State Before:  {status: 'pending'}
Pull Request:      {bot_id: 'bot-001'}
                   ↓
Lock Acquired:     {status: 'locked', locked_by: 'bot-001', locked_at: <now>}
Response:          {job_id, url, timeout_seconds: 600, locked_until: <now + 600s>}
```

### Lock TTL (Time-To-Live)

Default: **600 seconds** (10 minutes)

- Bot has 600s to execute crawl + submit result
- If submit doesn't arrive within 600s, lock expires
- Job can be re-pulled by another bot (or stays LOCKED until admin action)

### Race Conditions (Safely Handled)

**Scenario 1**: Bot A and B both request same job

```
Bot A: pull() → acquires lock → {status: 'locked', locked_by: 'bot-001'}
Bot B: pull() → lock already held → Job not in results, skipped += 1
```

**Scenario 2**: Bot submits after lock expires

```
Job: {status: 'locked', locked_at: <10 mins ago>}
Bot: submit() → {success: false, error: 'lock_expired'}
```

**Scenario 3**: Multiple bots, each gets different jobs

```
Pull request: max_jobs=5
System finds 10 PENDING jobs
Bot A: gets jobs [1,2,3,4,5]
Bot B: gets jobs [6,7,8,9,10]
```

### Idempotency Notes

- **Pull is idempotent**: Calling pull multiple times won't re-lock same job
- **Submit is NOT idempotent**: Calling submit twice creates 2 CrawlResult records (beware!)
- **Recommendation**: Submit only once per job, implement client-side deduplication

---

## Retry Logic

### Automatic Retry on Failure

```
Crawl fails → submit(success=false)
                ↓
retry_count < max_retries?
    ├─ YES → Job transitions to PENDING, auto-requeued
    └─ NO → Job transitions to FAILED, policy backoff
```

### Retry Count Tracking

```python
job.retry_count  # Current retry number (0, 1, 2, ...)
job.max_retries  # Max allowed (e.g., 3)
job.can_retry()  # Boolean: retry_count < max_retries
```

### Exponential Backoff (Policy)

Policy reschedules with exponential backoff on failure:

```
1st failure: wait 5 minutes
2nd failure: wait 10 minutes
3rd failure: wait 20 minutes
4th failure: wait 40 minutes (capped)
```

Configurable via `policy.retry_backoff_minutes` (default 5).

### Retry Recommendations

1. **Don't retry immediately**: Use exponential backoff on client side
2. **Network errors**: Retry with backoff
3. **Temporary failures**: Retry with backoff
4. **Permanent failures** (404, auth error): Don't retry, submit with error_msg
5. **Timeout**: Increase local timeout, or reduce jobs per pull

---

## Best Practices

### 1. Proper Error Handling

```python
import os
import requests
import time
from decimal import Decimal

BASE_URL = 'http://localhost:8005/api/crawl'
BOT_ID = os.environ.get('BOT_ID', 'bot-001')
API_TOKEN = os.environ.get('BOT_API_TOKEN', '')

if not API_TOKEN:
    raise SystemExit("BOT_API_TOKEN is required")


def crawl_and_submit(job_id, url, bot_id=BOT_ID, api_token=API_TOKEN):
    """Execute crawl and submit result with proper error handling."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        price = Decimal(extract_price(response.text))

        submit_result = requests.post(
            f"{BASE_URL}/submit/",
            json={
                'bot_id': bot_id,
                'api_token': api_token,
                'job_id': str(job_id),
                'success': True,
                'price': float(price),
                'currency': 'USD',
                'title': extract_title(response.text),
                'in_stock': extract_stock(response.text),
                'parsed_data': {'source': 'selenium'},
            },
            timeout=10
        )

        if not submit_result.json().get('success'):
            raise Exception(f"Submit failed: {submit_result.json()}")

        return True

    except requests.Timeout:
        submit_failure(job_id, bot_id, api_token, "Request timeout after 30s")
        return False

    except requests.HTTPError as e:
        if e.response.status_code in [404, 403]:
            submit_failure(job_id, bot_id, api_token, f"HTTP {e.response.status_code}")
            return False
        submit_failure(job_id, bot_id, api_token, f"HTTP {e.response.status_code}")
        return False

    except Exception as e:
        submit_failure(job_id, bot_id, api_token, str(e))
        return False


def submit_failure(job_id, bot_id, api_token, error_msg):
    """Submit crawl failure."""
    try:
        requests.post(
            f"{BASE_URL}/submit/",
            json={
                'bot_id': bot_id,
                'api_token': api_token,
                'job_id': str(job_id),
                'success': False,
                'error_msg': error_msg[:500],  # Truncate to 500 chars
            },
            timeout=10
        )
    except Exception as e:
        print(f"Failed to submit failure: {e}")
```

### 2. Graceful Shutdown

```python
import signal

def graceful_shutdown(signum, frame):
    """Handle shutdown signal."""
    print("Shutdown signal received, finishing current jobs...")
    # Don't pull new jobs
    # Wait for in-flight jobs to complete
    # Don't hold locks
    exit(0)

signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)
```

### 3. Monitoring & Logging

```python
import os
import logging
import time
import requests

logger = logging.getLogger('crawl_bot')

BASE_URL = 'http://localhost:8005/api/crawl'
BOT_ID = os.environ.get('BOT_ID', 'bot-001')
API_TOKEN = os.environ.get('BOT_API_TOKEN', '')

def pull_and_execute(bot_id=BOT_ID, api_token=API_TOKEN):
    """Pull jobs and execute with logging."""
    start = time.time()
    
    # Pull
    pull_resp = requests.post(
        f'{BASE_URL}/pull/',
        json={'bot_id': bot_id, 'api_token': api_token, 'max_jobs': 5},
        timeout=10
    )
    
    if not pull_resp.json().get('success'):
        logger.error(f"Pull failed: {pull_resp.json()}")
        return
    
    jobs = pull_resp.json()['data']['jobs']
    logger.info(f"Pulled {len(jobs)} jobs")
    
    # Execute each job
    for job in jobs:
        job_start = time.time()
        try:
            success = crawl_and_submit(job['job_id'], job['url'], bot_id, api_token)
            duration = time.time() - job_start
            logger.info(f"Job {job['job_id']}: {success} ({duration:.2f}s)")
        except Exception as e:
            duration = time.time() - job_start
            logger.error(f"Job {job['job_id']}: error {e} ({duration:.2f}s)")
    
    total = time.time() - start
    logger.info(f"Batch completed in {total:.2f}s")
```

### 4. Rate Limiting

```python
import os
import time
import requests

BASE_URL = 'http://localhost:8005/api/crawl'
BOT_ID = os.environ.get('BOT_ID', 'bot-001')
API_TOKEN = os.environ.get('BOT_API_TOKEN', '')

def pull_with_backoff(bot_id=BOT_ID, api_token=API_TOKEN, max_jobs=5):
    """Pull with exponential backoff on failure."""
    wait = 1  # seconds
    max_wait = 60
    
    while True:
        try:
            resp = requests.post(
                f'{BASE_URL}/pull/',
                json={
                    'bot_id': bot_id,
                    'api_token': api_token,
                    'max_jobs': max_jobs,
                },
                timeout=10
            )
            
            if resp.json().get('success'):
                return resp.json()['data']['jobs']
            
            # API error - backoff
            print(f"Pull failed, waiting {wait}s...")
            time.sleep(wait)
            wait = min(wait * 2, max_wait)
            
        except requests.Timeout:
            print(f"Pull timeout, waiting {wait}s...")
            time.sleep(wait)
            wait = min(wait * 2, max_wait)
```

### 5. Handling Competitive Environment

```python
import os
import requests

BASE_URL = 'http://localhost:8005/api/crawl'
API_TOKEN = os.environ.get('BOT_API_TOKEN', '')

def adaptive_pull(bot_id):
    """Adapt to competitive environment."""
    resp = requests.post(
        f'{BASE_URL}/pull/',
        json={
            'bot_id': bot_id,
            'api_token': API_TOKEN,
            'max_jobs': 10,
        },
        timeout=10
    )

    data = resp.json()['data']
    jobs_assigned = data['count']
    jobs_skipped = data['skipped']

    print(f"Assigned: {jobs_assigned}, Skipped: {jobs_skipped}")

    # If many jobs are being skipped, reduce request size
    if jobs_skipped > jobs_assigned * 2:
        # Too much contention - try smaller batches
        print("High contention detected, reducing batch size")
        return pull_with_backoff(bot_id, API_TOKEN, max_jobs=3)

    return data['jobs']
```

---

## Examples

### Example 1: Simple Sequential Bot

```python
#!/usr/bin/env python3
"""Simple bot that pulls and executes jobs sequentially."""

import requests
import sys
import os
from decimal import Decimal

BASE_URL = 'http://localhost:8005/api/crawl'
BOT_ID = sys.argv[1] if len(sys.argv) > 1 else 'bot-001'
API_TOKEN = os.environ.get('BOT_API_TOKEN', '')  # Get from environment

if not API_TOKEN:
    print("Error: BOT_API_TOKEN environment variable not set")
    sys.exit(1)

def fetch_job(job_id, url):
    """Fetch URL and extract data."""
    # In real bot, use Selenium, BeautifulSoup, Playwright, etc.
    # This is simplified mock
    return {
        'price': Decimal('99.99'),
        'title': 'Mock Product',
        'in_stock': True,
    }

def main():
    while True:
        # Pull jobs with authentication
        pull_resp = requests.post(
            f'{BASE_URL}/pull/',
            json={
                'bot_id': BOT_ID,
                'api_token': API_TOKEN,
                'max_jobs': 1
            }
        )
        
        if not pull_resp.ok:
            error = pull_resp.json()
            print(f"Pull failed: {error.get('error')} - {error.get('detail')}")
            continue
        
        jobs = pull_resp.json()['data']['jobs']
        if not jobs:
            print("No jobs available")
            continue
        
        # Execute each job
        for job in jobs:
            print(f"Executing {job['url']}...")
            
            try:
                result = fetch_job(job['job_id'], job['url'])
                
                # Submit result with authentication
                submit_resp = requests.post(
                    f'{BASE_URL}/submit/',
                    json={
                        'bot_id': BOT_ID,
                        'api_token': API_TOKEN,
                        'job_id': job['job_id'],
                        'success': True,
                        'price': float(result['price']),
                        'currency': 'USD',
                        'title': result['title'],
                        'in_stock': result['in_stock'],
                    }
                )
                
                if submit_resp.ok:
                    print(f"✓ Job {job['job_id']} completed")
                else:
                    error = submit_resp.json()
                    print(f"✗ Submit failed: {error.get('error')} - {error.get('detail')}")
                    
            except Exception as e:
                print(f"✗ Error: {e}")

if __name__ == '__main__':
    main()
```

**Usage**:
```bash
export BOT_API_TOKEN="bot_bot-001_Xk5m_lJ9k8N..."
python simple_bot.py bot-001
```

### Example 2: Parallel Bot with Thread Pool

```python
#!/usr/bin/env python3
"""Bot that pulls and executes jobs in parallel using threads."""

import requests
import concurrent.futures
import threading
import os
from queue import Queue

BOT_ID = 'bot-001'
API_TOKEN = os.environ.get('BOT_API_TOKEN', '')
WORKERS = 4
BASE_URL = 'http://localhost:8005/api/crawl'

job_queue = Queue()
semaphore = threading.Semaphore(WORKERS)

def worker():
    """Worker thread that processes jobs from queue."""
    while True:
        job = job_queue.get()
        if job is None:
            break
        
        with semaphore:
            try:
                # Execute crawl
                print(f"[{threading.current_thread().name}] Processing {job['url']}")
                
                # Mock execution
                import time
                time.sleep(2)
                
                # Submit result with authentication
                requests.post(
                    f'{BASE_URL}/submit/',
                    json={
                        'bot_id': BOT_ID,
                        'api_token': API_TOKEN,
                        'job_id': job['job_id'],
                        'success': True,
                        'price': 99.99,
                        'currency': 'USD',
                    }
                )
                
                print(f"[{threading.current_thread().name}] ✓ Done")
            except Exception as e:
                print(f"[{threading.current_thread().name}] ✗ Error: {e}")
            finally:
                job_queue.task_done()

def main():
    # Start workers
    threads = []
    for i in range(WORKERS):
        t = threading.Thread(target=worker, name=f'Worker-{i}', daemon=True)
        t.start()
        threads.append(t)
    
    # Pull and enqueue jobs
    while True:
        try:
            resp = requests.post(
                f'{BASE_URL}/pull/',
                json={
                    'bot_id': BOT_ID,
                    'api_token': API_TOKEN,
                    'max_jobs': WORKERS * 2
                },
                timeout=10
            )
            
            jobs = resp.json()['data']['jobs']
            print(f"Pulled {len(jobs)} jobs")
            
            for job in jobs:
                job_queue.put(job)
            
            # Wait before next pull
            import time
            time.sleep(10)
            
        except Exception as e:
            print(f"Pull error: {e}")

if __name__ == '__main__':
    main()
```

---

## Troubleshooting

### Q: Authentication failed errors

**Cause**: Missing or invalid bot_id/api_token

**Solutions**:
1. Go to Django Admin → Bot Configuration
2. Find your bot and copy the API Token
3. Set environment variable: `export BOT_API_TOKEN="your_token_here"`
4. Verify bot is enabled in admin
5. Check bot_id matches exactly (case-sensitive)

### Q: Bot is disabled error

**Cause**: Bot config has `enabled=False`

**Solutions**:
1. Go to Django Admin → Bot Configuration
2. Find your bot
3. Check "Enabled" checkbox
4. Save

---

### Q: Job stuck in LOCKED state

**Cause**: Bot crashed/disconnected without submitting result, lock TTL expired

**Solution**:
- Admin can manually reset job via admin panel (mark as PENDING)
- Or wait for lock expiration (10 minutes default)
- Management command: `python manage.py expire_locks`

### Q: "Already locked" errors in competitive environment

**Cause**: Multiple bots pulling same jobs simultaneously

**Solutions**:
1. Increase max_jobs per pull (reduce contention)
2. Use domain filter to split work
3. Reduce number of bots
4. Implement bot-specific job assignment

### Q: Submit fails with "not_assigned"

**Cause**: Submitted job_id doesn't match locked_by bot_id

**Solutions**:
1. Verify you're submitting correct job_id
2. Verify bot_id in submit matches bot_id in pull
3. Don't share pulled jobs between bots

### Q: Lock timeout before submission

**Cause**: Job execution takes longer than TTL (600s)

**Solutions**:
1. Increase local timeouts
2. Pull fewer jobs (max_jobs=1)
3. Increase job.lock_ttl_seconds in admin
4. Optimize crawl logic (reduce execution time)

### Q: Policy never reschedules

**Cause**: Job stuck in non-terminal state (PENDING, LOCKED, EXPIRED)

**Solutions**:
1. Submit result to transition to DONE/FAILED
2. Admin can force transition
3. Check policy.next_run_at in admin

### Q: Price validation errors

**Cause**: Price format invalid

**Solutions**:
- Ensure price is number: `99.99` (not string `"99.99"`)
- Ensure currency is exactly 3 chars: `USD`, not `USDA`
- Ensure price >= 0: no negative prices

---

## Support

For questions or issues:

1. Check this guide first
2. Review admin dashboard: `/admin/secure-admin-2025/`
3. Check application logs for detailed errors
4. Contact system admin for persistent issues

---

## Glossary

- **Bot**: External worker that pulls jobs and submits results
- **Job**: Individual URL execution with state tracking
- **Policy**: Definition of when/how URL should be crawled
- **Result**: Outcome submitted by bot (price, stock, etc.)
- **Lock**: Prevents concurrent execution of same job
- **TTL**: Time-To-Live for job lock
- **State**: Current execution phase (PENDING, LOCKED, DONE, FAILED, EXPIRED)
- **Retry**: Automatic re-queueing for failed crawls with retries remaining
- **Idempotent**: Operation produces same result on repeated calls

---

## Quick Reference Card

### Bot Workflow Checklist

```
1. Setup:
   □ Get bot_id from admin
   □ Get api_token from admin
   □ Set environment variable: export BOT_API_TOKEN="..."

2. Pull Loop:
   □ POST /api/crawl/pull/ with bot_id + api_token
   □ Check response.success
   □ Get jobs[] array from response.data
   □ Note: skipped shows jobs locked by others

3. Execute Each Job:
   □ Parse job.url
   □ Respect job.timeout_seconds (default 600s)
   □ Track job.locked_until deadline
   □ Extract price, currency, title, in_stock

4. Submit Result:
   □ POST /api/crawl/submit/ with bot_id + api_token + job_id
   □ If success: include price, currency (required)
   □ If failure: include error_msg (optional)
   □ Check response for new status

5. Handle Errors:
   □ 401/403 → Check credentials
   □ 400 job_not_locked → Job already processed
   □ 403 not_assigned → Wrong bot_id
   □ 400 lock_expired → Took too long
```

### State Quick Reference

| State | Bot Can Pull? | Bot Can Submit? | Terminal? |
|-------|---------------|-----------------|----------|
| pending | ✅ Yes | ❌ No | No |
| locked | ❌ No | ✅ Yes (owner only) | No |
| done | ❌ No | ❌ No | ✅ Yes |
| failed | ❌ No | ❌ No | ✅ Yes |
| expired | ❌ No | ❌ No | Admin reset |

### API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|  
| POST | `/api/crawl/pull/` | Get PENDING jobs, acquire locks |
| POST | `/api/crawl/submit/` | Submit result, transition state |

---

**Last Updated**: 2026-01-07  
**API Version**: 1.1  
**Crawl Service Version**: 2.1 (State Machine with Authentication)
