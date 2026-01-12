# Async Auto-Record Deployment Checklist

## Pre-Deployment Verification

- [ ] All code files checked and no errors
  ```bash
  python manage.py check
  ```

- [ ] Redis is running and accessible
  ```bash
  redis-cli ping
  # Expected: PONG
  ```

- [ ] Auto-record config enabled
  ```bash
  cat services/crawl_service/infrastructure/auto_record_config.json
  # Check: "enabled": true
  ```

---

## Deployment Steps

### 1. Verify New Files
```bash
ls -la services/crawl_service/infrastructure/auto_record_queue.py
# Should exist and be 227 lines

# Check other changes
git diff services/crawl_service/signals.py
git diff services/crawl_service/scheduler.py
git diff services/crawl_service/management/commands/run_crawl_scheduler.py
```

### 2. Restart Django
```bash
systemctl restart gunicorn-saas.service
# or
supervisorctl restart crawl-service
```

### 3. Start Scheduler (if not running)
```bash
# Option 1: Manual background
nohup python manage.py run_crawl_scheduler > /var/log/crawl_scheduler.log 2>&1 &

# Option 2: Systemd service (create if not exists)
# See deployment-systemd.service below

# Option 3: Supervisord (create if not exists)
# See deployment-supervisor.conf below

# Verify running
ps aux | grep run_crawl_scheduler
```

### 4. Monitor Initial Processing
```bash
tail -f /var/log/django/crawl_service.log

# Look for:
# [crawl_service] ✓ Enqueued CrawlResult ... for auto-record processing
# [crawl_service] Auto-record: processed=... recorded=...
```

### 5. Check Queue Status
```bash
python manage.py shell

from services.crawl_service.infrastructure.auto_record_queue import get_auto_record_queue_status
print(get_auto_record_queue_status())

# Expected: {'queue_size': <decreasing>, 'processing_size': 0, 'failed_size': 0}
```

---

## Post-Deployment Verification

### Checklist
- [ ] Scheduler is running (check ps)
- [ ] Queue is processing (check queue_size decreasing)
- [ ] CrawlResults are being recorded (check logs)
- [ ] No errors in logs
- [ ] Redis queue keys exist
  ```bash
  redis-cli
  > KEYS "crawl:auto_record:*"
  # Should show: 
  # crawl:auto_record:queue
  # crawl:auto_record:processing
  # crawl:auto_record:failed
  ```

### Performance Check
```bash
# Monitor queue depth
watch -n 5 'redis-cli LLEN "crawl:auto_record:queue"'

# Expected: Decreasing or stable (not growing indefinitely)

# Check recorded count (in app logs every 30s)
tail -f /var/log/django/crawl_service.log | grep "Auto-record:"

# Expected: processed=100 recorded=85 duplicates=10 failed=5 (or similar)
```

---

## Optional: Systemd Service Setup

Create `/etc/systemd/system/crawl-auto-record-scheduler.service`:

```ini
[Unit]
Description=Crawl Service Auto-Record Queue Scheduler
After=network.target redis.service
Wants=redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/PriceSynC/Saas_app
Environment=DJANGO_SETTINGS_MODULE=config.settings
ExecStart=/usr/bin/python3 manage.py run_crawl_scheduler \
  --interval=60 \
  --timeout-check-interval=30
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable crawl-auto-record-scheduler
sudo systemctl start crawl-auto-record-scheduler

# Verify
sudo systemctl status crawl-auto-record-scheduler
```

---

## Optional: Supervisord Setup

Create `/etc/supervisor/conf.d/crawl-auto-record-scheduler.conf`:

```ini
[program:crawl-auto-record-scheduler]
command=/usr/bin/python3 /var/www/PriceSynC/Saas_app/manage.py run_crawl_scheduler --interval=60 --timeout-check-interval=30
directory=/var/www/PriceSynC/Saas_app
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/crawl-auto-record-scheduler.err.log
stdout_logfile=/var/log/crawl-auto-record-scheduler.out.log
```

Activate:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start crawl-auto-record-scheduler

# Verify
sudo supervisorctl status crawl-auto-record-scheduler
```

---

## Troubleshooting After Deployment

### Issue: Queue not processing
```bash
# 1. Check scheduler is running
ps aux | grep run_crawl_scheduler

# 2. Check Redis
redis-cli ping

# 3. Check config enabled
cat services/crawl_service/infrastructure/auto_record_config.json

# 4. Run once to see errors
python manage.py run_crawl_scheduler --once
```

### Issue: High failure rate
```bash
# Check logs for reason
tail -f /var/log/django/crawl_service.log

# Check failed set
redis-cli
> SMEMBERS "crawl:auto_record:failed"

# Retry one
> RPUSH "crawl:auto_record:queue" "<result-id>"
```

### Issue: Scheduler crashed
```bash
# Restart
systemctl restart crawl-auto-record-scheduler

# Or manually
nohup python manage.py run_crawl_scheduler &
```

### Issue: Processing set stuck
```bash
# Clear (caution - may lose processing state)
redis-cli DEL "crawl:auto_record:processing"

# Restart scheduler
systemctl restart crawl-auto-record-scheduler
```

---

## Rollback (if needed)

**Note:** Not a true rollback, but reverting to sync auto-record:

1. Stop scheduler
   ```bash
   systemctl stop crawl-auto-record-scheduler
   ```

2. Restore old signal handler code
   ```bash
   git checkout HEAD~1 services/crawl_service/signals.py
   ```

3. Restart Django
   ```bash
   systemctl restart gunicorn-saas.service
   ```

4. Clear Redis queue
   ```bash
   redis-cli DEL "crawl:auto_record:queue"
   ```

**Note:** Results already written to PriceHistory will remain. Unprocessed queue items lost.

---

## Monitoring & Maintenance

### Daily
```bash
# Check queue depth
redis-cli LLEN "crawl:auto_record:queue"

# Check failed items
redis-cli SCARD "crawl:auto_record:failed"
```

### Weekly
```bash
# Check for stuck items
redis-cli SCARD "crawl:auto_record:processing"
# Should be 0 or very small

# Check scheduler logs for errors
grep ERROR /var/log/django/crawl_service.log | tail -20
```

### Monthly
```bash
# Analyze recorded vs failed ratio
# Check if config criteria too strict

# Review failed items
python manage.py shell
>>> from services.crawl_service.infrastructure.auto_record_queue import retry_failed_recordings
>>> retried = retry_failed_recordings(limit=1000)
>>> print(f"Retried {retried} items")
```

---

## Success Indicators

After deployment, you should see:

✅ Queue processing every 30 seconds
```
Auto-record: processed=100 recorded=85 duplicates=10 failed=5
```

✅ Queue depth stable or decreasing
```
LLEN "crawl:auto_record:queue" → 42 → 35 → 28 → ...
```

✅ No processing set backlog
```
SCARD "crawl:auto_record:processing" → 0 or 1-2
```

✅ Scheduler running without errors
```
systemctl status crawl-auto-record-scheduler → active (running)
```

✅ PriceHistory growing with AUTO source
```
SELECT * FROM price_history WHERE source='AUTO' ORDER BY created_at DESC LIMIT 10;
```

---

## Documentation References

- [Async Queue Architecture](./AUTO_RECORD_ASYNC_QUEUE.md)
- [Implementation Details](./AUTO_RECORD_ASYNC_IMPLEMENTATION.md)
- [Debugging Guide](./AUTO_RECORD_DEBUGGING.md)
- [Logic Fixes](./AUTO_RECORD_LOGIC_FIX.md)

