# Crawl Service Module

## Tổng Quan

Module **crawl_service** quản lý việc crawl giá sản phẩm tự động cho hệ thống SaaS. Đây là **hệ thống quản trị nội bộ** được quản lý hoàn toàn qua Django Admin.

### Đặc điểm chính:
- ✅ **Pure Layered Architecture** - Tuân thủ dependency rules nghiêm ngặt
- ✅ **Django Admin làm giao diện chính** - Không cần UI riêng
- ✅ **API tối thiểu** - Chỉ 2 endpoints cho bot nội bộ
- ✅ **Scheduler tự động** - Tạo jobs và theo dõi timeouts
- ✅ **Multi-tenant support** - Isolated per tenant

---

## Kiến Trúc

```
crawl_service/
├── domain/              # Pure business logic (NO framework dependencies)
│   ├── entities.py      # CrawlJob, CrawlTask, CrawlResult
│   ├── value_objects.py # PriceInfo, ScheduleConfig, BotIdentity
│   ├── services.py      # Domain services (pure business rules)
│   └── exceptions.py    # Domain exceptions
│
├── repositories/        # Data access abstractions
│   ├── interfaces.py    # Repository contracts
│   └── implementations.py # Django ORM implementations
│
├── infrastructure/      # Framework-specific code
│   ├── django_models.py # ORM models
│   └── scheduler.py     # Scheduler service
│
├── services/            # Application use cases
│   └── use_cases.py     # CreateJobs, PullJobs, SubmitResult
│
├── api/                 # MINIMAL - Only 2 bot endpoints
│   ├── serializers.py
│   ├── views.py         # BotPullJobsView, BotSubmitResultView
│   └── urls.py
│
├── admin/               # PRIMARY management interface
│   └── admin.py         # Full-featured Django Admin
│
├── management/          # Django commands
│   └── commands/
│       ├── run_crawl_scheduler.py
│       └── create_crawl_jobs.py
│
└── migrations/          # Database migrations
```

### Dependency Flow (Strict)

```
domain (no dependencies)
  ↑
repositories (depends on domain only)
  ↑
infrastructure (depends on domain + repositories)
  ↑
services (depends on domain + repositories)
  ↑
api + admin (depends on services)
```

---

## Luồng Nghiệp Vụ

### 1. Tạo Jobs (via Django Admin hoặc Command)

```bash
# Tạo jobs cho tất cả products của tenant
python manage.py create_crawl_jobs --tenant <uuid> --priority high

# Tạo jobs với lịch định kỳ (mỗi 2 giờ)
python manage.py create_crawl_jobs --tenant <uuid> --schedule "0 */2 * * *"
```

### 2. Scheduler Tự Động (Cron hoặc Celery Beat)

```bash
# Chạy scheduler (nên setup qua cron mỗi 5 phút)
*/5 * * * * python manage.py run_crawl_scheduler
```

**Scheduler làm gì:**
- Tìm jobs đến hạn thực thi
- Tạo tasks cho jobs đó
- Xử lý tasks timeout

### 3. Bot Pull Jobs (via API)

**Endpoint:** `POST /api/crawl/bot/pull/`

**Request:**
```json
{
  "bot_id": "bot-001",
  "max_tasks": 10
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "task_id": "uuid",
        "job_id": "uuid",
        "product_url": "https://example.com/product",
        "share_product_id": "uuid",
        "priority": 10,
        "timeout_at": "2026-01-06T10:30:00Z"
      }
    ],
    "count": 5
  }
}
```

### 4. Bot Submit Results (via API)

**Endpoint:** `POST /api/crawl/bot/submit/`

**Request:**
```json
{
  "task_id": "uuid",
  "bot_id": "bot-001",
  "price": 99.99,
  "currency": "USD",
  "in_stock": true,
  "product_title": "Product Name",
  "metadata": {
    "seller": "Shop XYZ",
    "rating": 4.5
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "result_id": "uuid",
    "task_id": "uuid",
    "job_id": "uuid",
    "share_product_id": "uuid",
    "price": 99.99,
    "currency": "USD",
    "in_stock": true,
    "crawled_at": "2026-01-06T10:25:30Z"
  }
}
```

### 5. Monitor qua Django Admin

Truy cập: `/admin/crawl_job/`, `/admin/crawl_task/`, `/admin/crawl_result/`

**Features:**
- ✅ View all jobs with status badges
- ✅ Filter by status, priority, tenant
- ✅ Search by URL, product ID
- ✅ Inline view tasks and results
- ✅ Bulk actions (reset, retry, create tasks)
- ✅ Detailed statistics per job
- ✅ Color-coded status indicators

---

## Setup & Cấu Hình

### 1. Thêm vào INSTALLED_APPS

```python
# config/settings.py

INSTALLED_APPS = [
    # ...
    'services.crawl_service',
    # ...
]
```

### 2. Include URLs

```python
# config/urls.py

urlpatterns = [
    # ...
    path('api/crawl/', include('services.crawl_service.api.urls')),
    # ...
]
```

### 3. Run Migrations

```bash
python manage.py makemigrations crawl_service
python manage.py migrate crawl_service
```

### 4. Setup Scheduler (Chọn 1 trong 3 cách)

#### Option A: Cron Job (Đơn giản nhất)

```bash
# Thêm vào crontab
*/5 * * * * cd /var/www/PriceSynC/Saas_app && python manage.py run_crawl_scheduler
```

#### Option B: Celery Beat (Production)

```python
# config/celery.py

from celery import Celery
from celery.schedules import crontab

app = Celery('pricesync')

app.conf.beat_schedule = {
    'run-crawl-scheduler': {
        'task': 'services.crawl_service.tasks.run_scheduler',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}
```

#### Option C: Systemd Timer (Linux)

```ini
# /etc/systemd/system/crawl-scheduler.service
[Unit]
Description=Crawl Scheduler

[Service]
Type=oneshot
WorkingDirectory=/var/www/PriceSynC/Saas_app
ExecStart=/usr/bin/python manage.py run_crawl_scheduler
```

```ini
# /etc/systemd/system/crawl-scheduler.timer
[Unit]
Description=Run Crawl Scheduler every 5 minutes

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```

---

## Sử Dụng Django Admin

### Quản Lý Jobs

1. **Tạo jobs thủ công:**
   - Không nên tạo thủ công, dùng command line
   
2. **Xem danh sách jobs:**
   - Filter theo status: pending, running, completed, failed
   - Search theo URL hoặc tenant_id
   - Sort theo priority, created_at

3. **Bulk actions:**
   - Reset to pending: Reset jobs về trạng thái pending
   - Mark as failed: Đánh dấu failed
   - Create tasks: Tạo tasks mới cho jobs
   - Reset retry count: Reset số lần retry

4. **View chi tiết job:**
   - Xem tất cả tasks của job
   - Xem results history
   - Xem statistics (success rate, avg time, etc.)

### Monitor Tasks

- Xem tasks đang chờ (queued)
- Xem tasks đã assign cho bot nào
- Check timeout tasks
- View completion time

### Xem Results

- Latest price cho mỗi product
- Price history
- In stock status
- Metadata from bot

---

## Domain Entities

### CrawlJob

```python
CrawlJob(
    id=UUID,
    tenant_id=UUID,
    share_product_id=UUID,
    product_url=str,
    priority=CrawlPriority,  # LOW, NORMAL, HIGH, URGENT
    status=JobStatus,         # PENDING, RUNNING, COMPLETED, FAILED, TIMEOUT
    schedule_rule=str,        # Cron expression (optional)
    next_run_at=datetime,     # Next execution time
    retry_count=int,
    max_retries=int,
    last_error=str
)
```

### CrawlTask

```python
CrawlTask(
    id=UUID,
    job_id=UUID,
    bot_id=str,
    status=TaskStatus,  # QUEUED, ASSIGNED, COMPLETED, FAILED
    assigned_at=datetime,
    completed_at=datetime,
    timeout_at=datetime
)
```

### CrawlResult

```python
CrawlResult(
    id=UUID,
    task_id=UUID,
    job_id=UUID,
    share_product_id=UUID,
    product_url=str,
    price=Decimal,
    currency=str,
    in_stock=bool,
    product_title=str,
    raw_html=str,
    metadata=dict,
    crawled_at=datetime
)
```

---

## Testing

```bash
# Run tests
python manage.py test services.crawl_service

# Test scheduler
python manage.py run_crawl_scheduler

# Test job creation
python manage.py create_crawl_jobs --tenant <uuid> --limit 5
```

---

## Troubleshooting

### Jobs không tự động chạy?
- Check scheduler đang chạy: `ps aux | grep run_crawl_scheduler`
- Check cron logs: `grep CRON /var/log/syslog`
- Verify jobs có `next_run_at` đúng

### Tasks bị timeout?
- Check timeout setting (default 10 phút)
- Check bot có đang chạy không
- Xem logs của bot

### Bot không pull được jobs?
- Check API endpoint: `curl -X POST http://localhost:8000/api/crawl/bot/pull/ -H "Content-Type: application/json" -d '{"bot_id":"test","max_tasks":1}'`
- Verify có tasks QUEUED trong database
- Check bot authentication

### Results không update share_product?
- Chức năng này cần integrate với products module
- Check `UpdateShareProductPriceUseCase` implementation

---

## TODO / Future Enhancements

- [ ] Bot authentication (API key hoặc JWT)
- [ ] Rate limiting cho bot endpoints
- [ ] Integrate với share_product update service
- [ ] Dashboard statistics (Grafana/Prometheus)
- [ ] Alert khi job failed nhiều lần
- [ ] Auto-retry failed jobs with exponential backoff
- [ ] Crawl result validation rules
- [ ] Historical price tracking and analysis

---

## License

Internal use only - PriceSynC SaaS Platform
