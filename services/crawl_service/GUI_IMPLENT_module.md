# Crawl Module – Implementation Guide
## (Pull-based Bot Architecture)

---

## 1. Mục tiêu của Crawl Module

Crawl Module là một module trung gian, độc lập với SaaS Core, có nhiệm vụ:

- Điều phối công việc crawl (job)
- Cho bot **chủ động pull job**
- Nhận kết quả crawl từ bot (push)
- Quản lý trạng thái job, retry, timeout
- Gửi dữ liệu crawl hợp lệ về SaaS Core

❌ Crawl Module KHÔNG crawl  
❌ Crawl Module KHÔNG chứa logic nghiệp vụ SaaS  
❌ Crawl Module KHÔNG phụ thuộc tenant logic  

---

## 2. Nguyên tắc kiến trúc cốt lõi

1. **Pull-based**: Bot chủ động lấy job
2. **1 Job = 1 URL**
3. **Job là ephemeral**, policy là persistent
4. **State-driven**: Bot chỉ lấy job theo trạng thái
5. **Idempotent**: Cron và bot chạy nhiều lần không gây trùng

---

## 3. Thành phần chính


[Crawl Module]
├── Scheduler
├── Job Store
├── Rule / Priority Engine
├── Bot API (Pull / Push)
└── Result Forwarder

[Crawl Bot]
├── Pull job
├── Crawl URL
└── Push result



---

## 4. Khái niệm dữ liệu chính

### 4.1 Crawl Job

Một Crawl Job đại diện cho **một lần crawl của một URL**.

**Đặc điểm:**
- Chỉ crawl 1 URL
- Có vòng đời ngắn
- Không tái sử dụng

---

### 4.2 Job Status (State Machine)

Crawl Job có **5 trạng thái chuẩn**:

PENDING → Job mới, chờ bot pull
LOCKED → Bot đã nhận job
DONE → Crawl thành công
FAILED → Crawl thất bại (quá retry)
EXPIRED → Bot không trả kết quả đúng hạn

yaml
Copy code

**Quy tắc:**
- Bot chỉ được pull job ở trạng thái `PENDING`
- `DONE / FAILED / EXPIRED` là trạng thái kết thúc
- `EXPIRED` có thể được scheduler reset để retry

---

## 5. Data Contract – Job

### 5.1 Job Payload gửi cho Bot (Pull)

Bot nhận được các thông tin tối thiểu:

- job_id
- url
- priority
- crawl_config (headers, js_required, timeout_hint)
- rule_set (selector, extract rule)

Bot **không cần biết**:
- Tenant
- Product
- Business logic

---

### 5.2 Job Result Bot gửi về (Push)

Bot gửi về:

- job_id
- status: success | fail
- data: dữ liệu crawl được (raw hoặc structured)
- meta:
  - crawl_duration
  - error (nếu có)
  - html_hash (tuỳ chọn)

Bot **không quyết định**:
- Lưu DB thế nào
- Retry hay không

---

## 6. Scheduler – Cơ chế tạo Job

### 6.1 Scheduler không tạo job theo cron cứng

❌ Sai:
- Cron mỗi ngày → tạo job cho tất cả URL

✅ Đúng:
- Cron chạy thường xuyên
- Scheduler chỉ tạo job khi **đến thời điểm cần crawl**

---

### 6.2 Crawl Policy (ngoài Job)

Mỗi URL có một crawl policy riêng:

- frequency (6h / 24h / 7d)
- last_success_at
- next_run_at
- priority_base

Scheduler:
- Quét policy
- So sánh `now >= next_run_at`
- Kiểm tra **không có active job**
- Tạo job mới ở trạng thái `PENDING`

---

## 7. Rule / Priority Engine

Rule Engine **KHÔNG parse HTML**.

Nhiệm vụ:
- Gán priority cho job
- Chọn queue phù hợp (js / http / special)

Priority có thể dựa trên:
- Độ quan trọng URL
- Độ lâu chưa crawl
- Tỉ lệ lỗi trước đó
- Business signal (hot product)

---

## 8. Bot Pull Mechanism

Bot định kỳ gọi API pull job.

Bot chỉ lấy job khi:
- job.status = PENDING
- capability match
- chưa vượt retry
- không bị lock

Khi pull thành công:
- Crawl Module chuyển job sang `LOCKED`
- Ghi nhận `locked_by`, `locked_at`

---

## 9. Timeout & Expiration

### 9.1 Lock TTL

Mỗi job khi `LOCKED` có một TTL (ví dụ 10–30 phút).

Nếu:
- Bot chết
- Bot không push result

→ Job chuyển sang `EXPIRED`

---

### 9.2 Retry Logic

- `EXPIRED` hoặc `FAILED` có thể:
  - retry (reset về `PENDING`)
  - hoặc kết thúc vĩnh viễn

Retry policy:
- max_retry
- backoff
- giảm priority dần

---

## 10. Bot Push Result

Khi bot crawl xong:
- Push kết quả về Crawl Module
- Crawl Module kiểm tra:
  - job còn thuộc bot này không
  - trạng thái hợp lệ không

Sau đó:
- DONE → forward data
- FAILED → ghi nhận lỗi

---

## 11. Giao tiếp với SaaS Core

Crawl Module **KHÔNG ghi trực tiếp DB SaaS**.

Crawl Module chỉ:
- Gọi Application Service
- Hoặc emit event:
  - crawl.job.completed
  - crawl.job.failed

SaaS Core tự xử lý:
- Lưu product
- Lưu price history
- Áp dụng tenant logic

---

## 12. Monitoring & Observability

Crawl Module nên theo dõi:

- Jobs created / hour
- Jobs done / failed / expired
- Bot activity
- Avg crawl duration
- Retry rate

---

## 13. Nguyên tắc mở rộng trong tương lai

- Khi cần crawl category → tạo Job Group
- Khi crawl pipeline phức tạp → tách Job / Task
- Khi tải lớn → thêm Redis queue
- Khi nhiều bot → thêm capability routing

---

## 14. Tóm tắt ngắn gọn

- Crawl Module = bộ điều phối
- 1 Job = 1 URL
- Bot pull – không push job
- Job chạy theo trạng thái
- Scheduler tạo job theo policy, không theo cron cứng
- SaaS Core không biết bot tồn tại

---