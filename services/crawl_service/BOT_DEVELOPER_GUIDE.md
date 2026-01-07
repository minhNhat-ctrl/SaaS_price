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

### Pull-Based Bot Architecture

The Crawl Service uses a **pull-based** architecture where bots actively request work:

```
┌─────────────────────────────────────────────────────────────┐
│ Crawl Service (Django backend)                              │
│  - CrawlPolicy: Define when URLs should be crawled         │
│  - CrawlJob: Individual execution with state machine       │
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

### State Machine: Job Lifecycle

Every crawl job follows a deterministic state machine:

```
      ┌─────────┐
      │ PENDING │  (ready to crawl, no lock held)
      └────┬────┘
           │ bot pulls job → lock acquired
           │
      ┌────▼─────┐
      │  LOCKED   │  (bot is executing, lock held for TTL)
      └┬───────┬──┘
       │       │
       │       └──→ timeout TTL exceeded
       │            ▼
       │       ┌────────────┐
       │       │  EXPIRED   │  (lock TTL exceeded, bot didn't respond)
       │       └────────────┘
       │
       ├─→ crawl succeeded
       │    ▼
       │  ┌────┐
       │  │DONE│  (result saved, policy rescheduled)
       │  └────┘
       │
       └─→ crawl failed
            ├─→ retries remaining
            │    ▼
            │  ┌────────┐
            │  │PENDING │  (auto-transitioned for retry)
            │  └────────┘
            │
            └─→ no retries left
                 ▼
              ┌────────┐
              │ FAILED │  (permanent failure, policy adjusted)
              └────────┘
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

### 1. Authenticate (optional, currently AllowAny)

No authentication required currently. All endpoints are public.

### 2. Bot Pulls a Job

```bash
curl -X POST http://localhost:8000/api/crawl/pull/ \
  -H "Content-Type: application/json" \
  -d '{
    "bot_id": "bot-001",
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

### 3. Bot Executes the Job

Bot now has 10 minutes (600s) to:
- Fetch the URL
- Extract data (price, stock, etc.)
- Parse the HTML/JSON
- Submit the result

### 4. Bot Submits Result

```bash
curl -X POST http://localhost:8000/api/crawl/submit/ \
  -H "Content-Type: application/json" \
  -d '{
    "bot_id": "bot-001",
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

### POST /api/crawl/pull/

Bot requests available PENDING jobs to execute.

#### Request

```json
{
  "bot_id": "string (required, max 100 chars)",
  "max_jobs": "integer (optional, default 10, max 100)",
  "domain": "string (optional, filter by domain like 'example.com')"
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
        "timeout_seconds": "integer (lock TTL)",
        "retry_count": "integer (current retries)",
        "locked_until": "ISO 8601 datetime"
      }
    ],
    "count": "integer",
    "skipped": "integer (already locked by other bots)"
  }
}
```

#### Errors

| Status | Error | Meaning |
|--------|-------|---------|
| 400 | `validation_error` | Invalid request data (missing bot_id, etc.) |
| 500 | `internal_error` | Server error |

---

### POST /api/crawl/submit/

Bot submits crawl result after executing job.

#### Request (Success Case)

```json
{
  "bot_id": "string (required, must match job lock)",
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

#### Request (Failure Case)

```json
{
  "bot_id": "string",
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
    "policy_next_run": "ISO 8601 (when policy will next run)"
  }
}
```

#### Response (Failure - Auto Retry)

If `retry_count < max_retries`, job auto-transitions to PENDING:

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

If `retry_count >= max_retries`, job transitions to FAILED:

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
| 404 | `job_not_found` | Job ID doesn't exist |
| 400 | `job_not_locked` | Job is not in LOCKED state (can't submit) |
| 403 | `not_assigned` | Job locked by different bot |
| 400 | `lock_expired` | Lock TTL exceeded, job marked as EXPIRED |
| 500 | `internal_error` | Server error |

---

## State Machine

### State Transitions

#### PENDING State
- **Entry**: Policy-created, or auto-transitioned after failure with retries remaining
- **Actions**: Wait to be pulled by bot
- **Exit**: Bot calls pull → transitions to LOCKED
- **Timeout**: None (can stay indefinitely)

#### LOCKED State
- **Entry**: Bot calls pull successfully
- **Duration**: `lock_ttl_seconds` (default 600s = 10 minutes)
- **Bot Action**: Execute crawl, must call submit before TTL expires
- **Exit Paths**:
  - **DONE**: submit with `success=true` → result saved, policy rescheduled
  - **FAILED**: submit with `success=false` + no retries → permanent failure
  - **PENDING**: submit with `success=false` + retries remaining → auto-retry
  - **EXPIRED**: TTL exceeded without submit → lock released, auto-transitioned back to PENDING (or EXPIRED if admin mark)

#### DONE State
- **Entry**: submit with `success=true`
- **Result**: CrawlResult record created with price, stock, etc.
- **Final**: No further transitions
- **Policy**: Rescheduled based on `frequency_hours`

#### FAILED State
- **Entry**: submit with `success=false` + no retries remaining
- **Final**: No further transitions
- **Policy**: Rescheduled with exponential backoff based on `retry_backoff_minutes`

#### EXPIRED State
- **Entry**: Lock TTL exceeded without bot response
- **Reason**: Bot likely crashed or network timeout
- **Admin Recovery**: Can manually reset to PENDING
- **Auto Recovery**: Management command finds and marks expired

### Reading Current State

```python
job.status  # 'pending', 'locked', 'done', 'failed', 'expired'
job.locked_by  # Bot ID holding lock (if LOCKED)
job.locked_at  # When lock was acquired (if LOCKED)
job.lock_ttl_seconds  # Duration of lock (600)
job.is_lock_expired()  # True if LOCKED and TTL exceeded
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
import requests
import time
from decimal import Decimal

def crawl_and_submit(job_id, url, bot_id="bot-001"):
    """
    Execute crawl and submit result with proper error handling.
    """
    try:
        # Fetch URL with timeout
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse and extract data
        price = Decimal(extract_price(response.text))
        
        # Submit result
        submit_result = requests.post(
            'http://localhost:8000/api/crawl/submit/',
            json={
                'bot_id': bot_id,
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
        # Network timeout - let bot retry with exponential backoff
        submit_failure(job_id, bot_id, "Request timeout after 30s")
        return False
        
    except requests.HTTPError as e:
        if e.response.status_code in [404, 403]:
            # Permanent error - don't retry
            submit_failure(job_id, bot_id, f"HTTP {e.response.status_code}")
            return False
        else:
            # Temporary error - allow retry
            submit_failure(job_id, bot_id, f"HTTP {e.response.status_code}")
            return False
            
    except Exception as e:
        submit_failure(job_id, bot_id, str(e))
        return False


def submit_failure(job_id, bot_id, error_msg):
    """Submit crawl failure."""
    try:
        requests.post(
            'http://localhost:8000/api/crawl/submit/',
            json={
                'bot_id': bot_id,
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
import logging
import time

logger = logging.getLogger('crawl_bot')

def pull_and_execute(bot_id):
    """Pull jobs and execute with logging."""
    start = time.time()
    
    # Pull
    pull_resp = requests.post(
        'http://localhost:8000/api/crawl/pull/',
        json={'bot_id': bot_id, 'max_jobs': 5},
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
            success = crawl_and_submit(
                job['job_id'],
                job['url'],
                bot_id
            )
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
import time

def pull_with_backoff(bot_id, max_jobs=5):
    """Pull with exponential backoff on failure."""
    wait = 1  # seconds
    max_wait = 60
    
    while True:
        try:
            resp = requests.post(
                'http://localhost:8000/api/crawl/pull/',
                json={'bot_id': bot_id, 'max_jobs': max_jobs},
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
def adaptive_pull(bot_id):
    """Adapt to competitive environment."""
    resp = requests.post(
        'http://localhost:8000/api/crawl/pull/',
        json={'bot_id': bot_id, 'max_jobs': 10},
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
        return pull_with_max_jobs(bot_id, max_jobs=3)
    
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
from decimal import Decimal

BASE_URL = 'http://localhost:8000/api/crawl'
BOT_ID = sys.argv[1] if len(sys.argv) > 1 else 'simple-bot-001'

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
        # Pull jobs
        pull_resp = requests.post(
            f'{BASE_URL}/pull/',
            json={'bot_id': BOT_ID, 'max_jobs': 1}
        )
        
        if not pull_resp.ok:
            print(f"Pull failed: {pull_resp.status_code}")
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
                
                # Submit result
                submit_resp = requests.post(
                    f'{BASE_URL}/submit/',
                    json={
                        'bot_id': BOT_ID,
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
                    print(f"✗ Submit failed: {submit_resp.json()}")
                    
            except Exception as e:
                print(f"✗ Error: {e}")

if __name__ == '__main__':
    main()
```

### Example 2: Parallel Bot with Thread Pool

```python
#!/usr/bin/env python3
"""Bot that pulls and executes jobs in parallel using threads."""

import requests
import concurrent.futures
import threading
from queue import Queue

BOT_ID = 'parallel-bot-001'
WORKERS = 4
BASE_URL = 'http://localhost:8000/api/crawl'

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
                
                # Submit result
                requests.post(
                    f'{BASE_URL}/submit/',
                    json={
                        'bot_id': BOT_ID,
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
                json={'bot_id': BOT_ID, 'max_jobs': WORKERS * 2},
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

**Last Updated**: 2025-01-07  
**API Version**: 1.0  
**Crawl Service Version**: 2.0 (State Machine)
