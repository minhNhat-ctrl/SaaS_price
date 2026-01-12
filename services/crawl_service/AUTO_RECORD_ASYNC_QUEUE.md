# Async Auto-Record via Redis Queue

## Architecture Change

**Before:** Synchronous auto-record on CrawlResult post_save signal
- ❌ Blocks signal handler on database write
- ❌ Potential database overload
- ❌ Missed results on error
- ❌ No retry mechanism

**After:** Asynchronous auto-record via Redis queue
- ✅ Non-blocking signal handler (just enqueues)
- ✅ Async processing by scheduler
- ✅ Automatic retry on failure
- ✅ No direct database load spike

---

## Data Flow

```
CrawlResult Created
    ↓
post_save signal fires
    ↓
auto_record_crawl_result()
    • Check if auto-record enabled
    • Enqueue result_id to Redis (non-blocking)
    • Return immediately
    ↓
[Fast, doesn't block signal handler]
    ↓
Scheduler (runs periodically, e.g., every 30s)
    ↓
process_auto_record_queue()
    • Pop from Redis queue (FIFO)
    • Get CrawlResult from DB
    • Check criteria (should_auto_record)
    • Write to PriceHistory
    • Update result.history_recorded* fields
    • Handle duplicates & failures
    ↓
[Async, doesn't affect request/response]
    ↓
Retry on failure
    • Failed results re-enqueued
    • Max retries: 3 (configurable)
    • Failed beyond retries go to failed set
    ↓
Periodic retry of permanently failed
    • Once per many cycles
    • Gives chance to recover
```

---

## Redis Data Structures

### Main Queue
- **Key:** `crawl:auto_record:queue` (Redis List)
- **Purpose:** FIFO queue of CrawlResult IDs to process
- **Operation:** RPUSH (enqueue), LPOP (dequeue)

### Processing Set
- **Key:** `crawl:auto_record:processing` (Redis Set)
- **Purpose:** Track IDs currently being processed (prevent duplicates)
- **Operation:** SADD (mark processing), SREM (unmark)

### Failed Set
- **Key:** `crawl:auto_record:failed` (Redis Set)
- **Purpose:** Track IDs that failed after max retries
- **Operation:** SADD (mark failed), SPOP (retry)

### Failure Counters
- **Key:** `crawl:auto_record:failures:{result_id}` (Redis String)
- **Purpose:** Track retry attempt count per result
- **TTL:** 1 hour (auto-expire)
- **Operation:** SET, GET, DELETE

---

## Components

### 1. Signal Handler (`signals.py`)
```python
@receiver(post_save, sender='crawl_service.CrawlResult')
def auto_record_crawl_result(sender, instance, created, **kwargs):
    # 1. Check if enabled
    # 2. Enqueue to Redis (non-blocking)
    # Returns immediately
```

**Key Change:** Instead of calling `write_price_history_for_result()` directly, calls `enqueue_auto_record()`.

### 2. Queue Manager (`infrastructure/auto_record_queue.py`)
**Functions:**
- `enqueue_auto_record(result_id)` - Add to queue
- `process_auto_record_queue()` - Process batch
- `retry_failed_recordings()` - Retry permanently failed
- `get_auto_record_queue_status()` - Get stats
- `clear_auto_record_queue()` - Reset queues

### 3. Scheduler Integration (`scheduler.py`)
```python
class CrawlScheduler:
    def process_auto_record_queue(self):
        # Called periodically by scheduler
        # Processes batch of 100 results
        # Auto-retries 3 times
        # Returns stats
```

### 4. Management Command (`management/commands/run_crawl_scheduler.py`)
**Already runs:**
- `create_tasks()` - Every cycle
- `handle_timeouts()` - Every 30s
- `retry_failed_jobs()` - Every 30s

**Now also runs:**
- `process_auto_record_queue()` - Every 30s (or configurable)

---

## Configuration

### Current Setup
The `run_crawl_scheduler` runs continuously with:
- **Create tasks interval:** 60 seconds (default)
- **Timeout/retry interval:** 30 seconds (default)

### In Gunicorn/Systemd
Start scheduler as service:
```bash
systemctl start crawl-scheduler  # or similar
systemctl enable crawl-scheduler
```

### Or manually:
```bash
python manage.py run_crawl_scheduler --interval=60 --timeout-check-interval=30
```

---

## Processing Algorithm

```python
def process_auto_record_queue(batch_size=100, max_retries=3):
    for _ in range(batch_size):
        # 1. Pop from queue
        result_id = client.lpop(QUEUE)
        if not result_id:
            break
        
        # 2. Check not already processing
        if already_processing(result_id):
            continue
        
        # 3. Mark as processing
        client.sadd(PROCESSING, result_id)
        
        try:
            # 4. Get result from DB
            result = CrawlResult.objects.get(id=result_id)
            
            # 5. Check criteria
            if not should_auto_record(result):
                continue  # Skip, don't retry
            
            # 6. Write to history
            success = write_price_history_for_result(result)
            
            # 7. Handle outcome
            if success:
                stats["recorded"] += 1
            elif duplicate:
                stats["duplicates"] += 1
            else:
                # Retry logic
                failures = get_failure_count(result_id)
                if failures < max_retries:
                    client.rpush(QUEUE, result_id)  # Re-enqueue
                    failures += 1
                else:
                    client.sadd(FAILED, result_id)  # Give up
                    stats["failed"] += 1
        
        finally:
            # 8. Unmark processing
            client.srem(PROCESSING, result_id)
    
    return stats
```

---

## Monitoring & Debugging

### Check Queue Status
```bash
python manage.py shell
>>> from services.crawl_service.infrastructure.auto_record_queue import get_auto_record_queue_status
>>> status = get_auto_record_queue_status()
>>> print(status)
{'queue_size': 42, 'processing_size': 0, 'failed_size': 3}
```

### Manual Processing (for testing)
```bash
python manage.py shell
>>> from services.crawl_service.scheduler import CrawlScheduler
>>> scheduler = CrawlScheduler()
>>> stats = scheduler.process_auto_record_queue()
>>> print(stats)
{'processed': 50, 'recorded': 42, 'duplicates': 5, 'failed': 3}
```

### Logs
Look for:
```
[crawl_service] ✓ Enqueued CrawlResult ... for auto-record processing
[crawl_service] Auto-record: processed=50 recorded=42 duplicates=5 failed=3 queue_remaining=10
```

### Clear Queues (for maintenance)
```bash
python manage.py shell
>>> from services.crawl_service.infrastructure.auto_record_queue import clear_auto_record_queue
>>> clear_auto_record_queue()
```

---

## Advantages Over Sync Approach

| Aspect | Sync (Old) | Async (New) |
|--------|-----------|------------|
| **Blocking** | ✓ Blocks signal handler | ✗ Non-blocking |
| **Load** | Peak load on write | Smooth, distributed |
| **Database** | Direct writes | Controlled batch writes |
| **Retries** | Manual action needed | Automatic retry |
| **Failed Results** | Lost on error | Preserved in Redis |
| **Scalability** | Limited | Scales with queue |
| **Monitoring** | Hard to debug | Redis queue visible |

---

## Common Issues & Solutions

### Issue: Queue not processing
**Check:**
1. Is scheduler running? `ps aux | grep run_crawl_scheduler`
2. Is Redis available? `redis-cli ping`
3. Check logs: `tail -f /var/log/django/crawl_service.log`

### Issue: Queue growing too fast
**Solution:**
1. Increase batch size: `--batch-size 200`
2. Run scheduler more frequently: `--timeout-check-interval 15`
3. Check if `should_auto_record()` is too strict

### Issue: Results stuck in processing set
**Recover:**
```bash
redis-cli del "crawl:auto_record:processing"
```

### Issue: Results in failed set not retrying
**Retry all:**
```bash
python manage.py shell
>>> from services.crawl_service.infrastructure.auto_record_queue import retry_failed_recordings
>>> retry_failed_recordings(limit=1000)
```

---

## Performance Metrics

**Target:**
- Process 100 results/min
- < 50ms per result (DB + criteria check + history write)
- Queue size < 1000 under normal load

**Monitoring:**
```bash
# Check every minute
watch 'python manage.py shell -c "
from services.crawl_service.infrastructure.auto_record_queue import get_auto_record_queue_status
print(get_auto_record_queue_status())
"'
```

---

## Future Improvements

1. **Metrics:** Add Prometheus metrics for queue depth, processing rate
2. **Dead Letter Queue:** Separate queue for analysis of failures
3. **Batch Write:** Write multiple PriceHistory in single transaction
4. **Priority Queue:** Process high-priority results first
5. **Alert:** Notify if queue depth exceeds threshold

---

## Related Files

- [Auto-Record Logic Fix](./AUTO_RECORD_LOGIC_FIX.md)
- [Auto-Record Debugging](./AUTO_RECORD_DEBUGGING.md)
- [Crawl Service README](./README.md)
