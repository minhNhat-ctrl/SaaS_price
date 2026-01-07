# Crawl Service - Quick Reference Guide

## 🚀 Quick Start for Developers

### For Bot Developers
See: [BOT_DEVELOPER_GUIDE.md](services/crawl_service/BOT_DEVELOPER_GUIDE.md)

### For Backend Developers
See: [CRAWL_SERVICE_STATE_MACHINE_IMPLEMENTATION.md](CRAWL_SERVICE_STATE_MACHINE_IMPLEMENTATION.md)

### For Admins/DevOps
See: [CRAWL_SERVICE_COMPLETE_STATUS.md](CRAWL_SERVICE_COMPLETE_STATUS.md)

---

## 📋 API Reference

### Endpoint 1: Pull Jobs
```bash
POST /api/crawl/pull/

Request:
{
  "bot_id": "bot-001",
  "max_jobs": 10,
  "domain": "example.com"  # optional
}

Response:
{
  "success": true,
  "data": {
    "jobs": [{
      "job_id": "uuid",
      "url": "https://...",
      "priority": 10,
      "max_retries": 3,
      "timeout_seconds": 600,
      "retry_count": 0,
      "locked_until": "2025-01-07T07:20:00Z"
    }],
    "count": 1,
    "skipped": 0
  }
}
```

### Endpoint 2: Submit Result
```bash
POST /api/crawl/submit/

Request (Success):
{
  "bot_id": "bot-001",
  "job_id": "uuid",
  "success": true,
  "price": 99.99,
  "currency": "USD",
  "title": "Product",
  "in_stock": true
}

Response:
{
  "success": true,
  "data": {
    "result_id": "uuid",
    "job_id": "uuid",
    "status": "done",
    "price": 99.99,
    "currency": "USD",
    "policy_next_run": "2025-01-08T06:54:00Z"
  }
}
```

---

## 🎯 State Machine

```
PENDING ──pull──> LOCKED ──submit(success)──> DONE
                     │
                     ├─ submit(fail, retries)
                     │  └─> PENDING (auto-retry)
                     │
                     ├─ submit(fail, no retries)
                     │  └─> FAILED
                     │
                     └─ TTL expires
                        └─> EXPIRED
```

---

## 🔒 Locking Mechanism

**Key Concept**: Only one bot can execute a job at a time.

- **Lock acquired**: When bot pulls job
- **Lock held by**: `bot_id` (field: `locked_by`)
- **Lock duration**: 10 minutes (field: `lock_ttl_seconds`)
- **Lock expires**: Automatically after TTL (prevents deadlock)

**Errors**:
- `job_already_locked`: Job held by another bot
- `lock_expired`: Your lock expired, pull again
- `not_assigned`: You don't own this job's lock

---

## 🔄 Retry Logic

**Exponential Backoff**:
- Failure 1: Wait 5 min
- Failure 2: Wait 10 min
- Failure 3: Wait 20 min
- Failure 4: Wait 40 min (exhausted)

**Auto-Retry**: If retries remain, job automatically returned to PENDING for next pull.

**Manual Control**: Configure per policy:
- `max_retries`: How many times to retry (default: 3)
- `retry_backoff_minutes`: Initial backoff (default: 5)

---

## 📊 Admin Interface

**Access**: `/admin/secure-admin-2025/`

### Monitoring Dashboards

**CrawlPolicyAdmin**:
- Create policies for URLs to crawl
- Set frequency (6h, 24h, 168h, etc.)
- Configure retry strategy
- View next scheduled run

**CrawlJobAdmin**:
- Monitor job execution
- See which bot is executing (locked_by)
- View retry count and remaining TTL
- Bulk actions: reset locks, mark expired

**CrawlResultAdmin**:
- View crawled data
- Check prices, stock status
- Review parsed data (JSON)

---

## 🐍 Python Bot Example

```python
import requests
import time

class CrawlBot:
    def __init__(self, bot_id, api_url):
        self.bot_id = bot_id
        self.api_url = api_url
    
    def pull_jobs(self, max_jobs=10):
        """Pull available jobs"""
        response = requests.post(
            f"{self.api_url}/api/crawl/pull/",
            json={
                "bot_id": self.bot_id,
                "max_jobs": max_jobs
            }
        )
        return response.json()["data"]["jobs"]
    
    def submit_result(self, job_id, price, currency, title, in_stock):
        """Submit successful crawl"""
        response = requests.post(
            f"{self.api_url}/api/crawl/submit/",
            json={
                "bot_id": self.bot_id,
                "job_id": str(job_id),
                "success": True,
                "price": price,
                "currency": currency,
                "title": title,
                "in_stock": in_stock
            }
        )
        return response.json()
    
    def submit_error(self, job_id, error_msg):
        """Submit failed crawl (will auto-retry)"""
        response = requests.post(
            f"{self.api_url}/api/crawl/submit/",
            json={
                "bot_id": self.bot_id,
                "job_id": str(job_id),
                "success": False,
                "error_msg": error_msg
            }
        )
        return response.json()
    
    def run(self):
        """Main bot loop"""
        while True:
            # Pull jobs
            jobs = self.pull_jobs(max_jobs=5)
            
            if not jobs:
                print("No jobs available, waiting...")
                time.sleep(30)
                continue
            
            for job in jobs:
                try:
                    # Crawl (pseudo-code)
                    price, currency = self.crawl(job["url"])
                    
                    # Submit success
                    self.submit_result(
                        job["job_id"],
                        price=price,
                        currency=currency,
                        title="Product",
                        in_stock=True
                    )
                    print(f"✓ {job['url']} → ${price} {currency}")
                    
                except Exception as e:
                    # Submit error (auto-retry)
                    self.submit_error(job["job_id"], str(e))
                    print(f"✗ {job['url']} → {e}")
    
    def crawl(self, url):
        """Pseudo crawl function"""
        # Your scraping logic here
        return 99.99, "USD"

# Usage
bot = CrawlBot("bot-001", "http://localhost:8000")
bot.run()
```

---

## 🚨 Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `job_not_found` | Job doesn't exist | Check job_id is from pull response |
| `job_already_locked` | Another bot is executing | Wait or admin reset |
| `lock_expired` | Your lock TTL exceeded | Pull job again (new lock) |
| `not_assigned` | You don't own lock | Only the bot that pulled can submit |
| `validation_error` | Missing/invalid fields | Check all required fields present |

---

## 📊 Database Tables

### CrawlPolicy
```
├─ id: UUID
├─ url: VARCHAR(2048) [unique, indexed]
├─ frequency_hours: INTEGER (6, 24, 168, ...)
├─ priority: INTEGER (1-20)
├─ max_retries: INTEGER
├─ retry_backoff_minutes: INTEGER
├─ timeout_minutes: INTEGER
├─ enabled: BOOLEAN [indexed]
├─ next_run_at: TIMESTAMP [indexed]
├─ failure_count: INTEGER
├─ last_success_at: TIMESTAMP
├─ last_failed_at: TIMESTAMP
└─ crawl_config: JSONB
```

### CrawlJob
```
├─ id: UUID
├─ policy_id: FK → CrawlPolicy [indexed]
├─ url: VARCHAR(2048)
├─ status: VARCHAR(20) [indexed]  # pending, locked, done, failed, expired
├─ priority: INTEGER
├─ locked_by: VARCHAR(100)  # bot ID
├─ locked_at: TIMESTAMP
├─ lock_ttl_seconds: INTEGER (600)
├─ retry_count: INTEGER
├─ max_retries: INTEGER
├─ error_msg: TEXT
└─ created_at: TIMESTAMP
```

### CrawlResult
```
├─ id: UUID
├─ job_id: FK → CrawlJob [unique]
├─ price: DECIMAL(10, 2)
├─ currency: VARCHAR(3)
├─ title: VARCHAR(500)
├─ in_stock: BOOLEAN
├─ parsed_data: JSONB
├─ raw_html: LONGTEXT
├─ crawled_at: TIMESTAMP
└─ created_at: TIMESTAMP
```

---

## 🔧 Management Commands (Future)

```bash
# Create jobs from policies (future)
python manage.py create_jobs_from_policies

# Expire old locks (future)
python manage.py expire_locks
```

---

## 📞 Support

**For detailed documentation**:
1. Bot Developers: See [BOT_DEVELOPER_GUIDE.md](services/crawl_service/BOT_DEVELOPER_GUIDE.md)
2. Backend Team: See [CRAWL_SERVICE_STATE_MACHINE_IMPLEMENTATION.md](CRAWL_SERVICE_STATE_MACHINE_IMPLEMENTATION.md)
3. DevOps/Admin: See [CRAWL_SERVICE_COMPLETE_STATUS.md](CRAWL_SERVICE_COMPLETE_STATUS.md)

**Admin Dashboard**: `/admin/secure-admin-2025/`

---

**Status**: ✅ Production Ready  
**Last Updated**: 2025-01-07  
**Version**: 2.0 (State Machine + Policy-Driven)
