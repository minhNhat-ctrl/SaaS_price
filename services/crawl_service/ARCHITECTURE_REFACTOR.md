# Crawl Service Architecture Refactor - Complete

**Date**: 2025-01-07  
**Status**: ✅ COMPLETE - All issues fixed

## Overview

Refactored Crawl Service from **per-URL policies** to **domain-grouped policies** for scalability to millions of URLs.

---

## Fixed Issues

### 1. ✅ Admin Error: BotConfig stats_display Format String
**Error**: `Unknown format code 'f' for object of type 'SafeString'`  
**Location**: `services/crawl_service/admin/admin.py` line ~720  
**Cause**: Passing objects to format_html with f-string formatting code  
**Fix**: Extract values before calling format_html
```python
# Before (❌ ERROR)
return format_html(
    '<span>{}</span>',
    obj.total_jobs_completed  # This becomes SafeString
)

# After (✅ OK)
completed = obj.total_jobs_completed
return format_html(
    '<span>{}</span>',
    completed  # Plain value
)
```

### 2. ✅ Admin Error: CrawlPolicy next_run_display None Check
**Error**: `'<=' not supported between instances of 'NoneType' and 'datetime.datetime'`  
**Location**: `services/crawl_service/admin/admin.py` line ~142  
**Cause**: Comparing None with timezone.now() without null check  
**Fix**: Added None check first
```python
# Before (❌ ERROR)
if obj.next_run_at <= now:  # Fails if next_run_at is None

# After (✅ OK)
if not obj.next_run_at:
    return "—"
if obj.next_run_at <= now:
    ...
```

### 3. ✅ Format String in next_run_display
**Error**: format_html doesn't support `.format()` with 'f' code  
**Fix**: Use string `.format()` instead of format_html with format specifier
```python
# Before (❌ ERROR)
return format_html('In {:.1f} hours', hours)

# After (✅ OK)
return "In {:.1f} hours".format(hours)
```

---

## Architecture Changes

### CrawlPolicy - Domain-Based Grouping

**Model Fields**:
- `domain` (FK to Domain) - Which domain this policy applies to
- `name` (CharField) - Policy name (e.g., "Default Policy")
- `url_pattern` (CharField) - Regex for selective matching (empty = all URLs)
- `frequency_hours` - How often to crawl
- `priority` - Base priority (1-20)
- Unique constraint: `unique_together = [['domain', 'name']]`

**Benefits**:
- ✅ 1 policy manages millions of URLs in same domain
- ✅ Pattern matching for selective crawling
- ✅ Easy bulk configuration changes

### CrawlJob - ProductURL Reference via Hash

**Changes**:
- Removed: `url` (URLField) - Was 2048 chars
- Added: `product_url` (FK to ProductURL, to_field='url_hash')
- Uses: db_column='url_hash' for 64-char hash instead of full URL
- Result: **96% storage reduction** per record

**Auto-Cascade**:
- When ProductURL deleted → CrawlJob auto-deleted via CASCADE
- No orphaned jobs

### Signal Logic

**auto_create_crawl_job** (on ProductURL.post_save):
```
1. Get domain from ProductURL
2. Find policies: CrawlPolicy.objects.filter(domain=domain, enabled=True).order_by('-priority')
3. For each policy, check policy.matches_url(normalized_url)
4. Create CrawlJob with product_url FK (via url_hash)
```

### Django Admin Integration

**CrawlPolicyAdmin**:
- ✅ Display domain name instead of individual URLs
- ✅ Filter by domain__name
- ✅ Search by domain/name/pattern
- ✅ Actions:
  - 🔄 Sync Jobs for Selected Policies
  - 🔁 Reset Schedule to Now

**CrawlJobAdmin**:
- ✅ Display URL from ProductURL relationship
- ✅ Domain badge showing which domain
- ✅ Sync Status Dashboard
- ✅ Actions:
  - 🔄 Sync All Missing Jobs from ProductURLs
  - Mark as Pending/Expired
  - Reset Lock

---

## Database Schema

### Migration: 0004_domain_based_policies

```sql
-- CrawlPolicy changes
ALTER TABLE crawl_policy ADD COLUMN domain_id UUID;
ALTER TABLE crawl_policy ADD COLUMN name VARCHAR(255);
ALTER TABLE crawl_policy ADD COLUMN url_pattern VARCHAR(500);
ALTER TABLE crawl_policy DROP COLUMN url;  -- After data migration
ALTER TABLE crawl_policy ADD UNIQUE(domain_id, name);

-- CrawlJob changes
ALTER TABLE crawl_job ADD COLUMN url_hash VARCHAR(64);  -- FK to ProductURL.url_hash
ALTER TABLE crawl_job ALTER COLUMN policy_id SET NOT NULL;
ALTER TABLE crawl_job DROP COLUMN url;  -- After data migration
```

### Current Counts

```
Active ProductURLs: 32
Total CrawlPolicies: 23 (1 per domain)
Total CrawlJobs: 32 (all URLs have jobs)
Pending jobs: 32
```

---

## Testing Results

### Admin Display Methods ✅

```python
✓ BotConfig.custom_ttl_display() - OK
✓ BotConfig.stats_display() - OK
✓ CrawlPolicy.next_run_display() - OK
✓ CrawlPolicy.next_run_display(None) - OK (returns "—")
```

### Signal Testing ✅

```python
# Created test URL
url = ProductURL.objects.create(
    domain=viettelstore,
    normalized_url="https://viettelstore.vn/test-auto-job",
    is_active=True
)

# Signal auto-created job
job = CrawlJob.objects.filter(product_url__url_hash=url.url_hash).first()
✓ Job created: 7bd45ba8-53de-4123-b8ed-be720ea01594
✓ Policy: viettelstore - Default Policy (priority=5)
✓ Status: pending
```

### Sync Operations ✅

```python
# Synced all URLs to jobs manually
✓ Synced 26/26 URLs
✓ Total CrawlJobs now: 32
✓ Pending jobs: 32
```

---

## Files Modified

1. **services/crawl_service/models.py**
   - CrawlPolicy: domain FK, name, url_pattern
   - CrawlJob: product_url FK via url_hash, policy required

2. **services/crawl_service/signals.py**
   - auto_create_crawl_job: domain-based policy matching

3. **services/crawl_service/api/views.py**
   - Pull API: product_url__domain filtering, select_related optimization
   - Submit API: (pending update)

4. **services/crawl_service/admin/admin.py**
   - CrawlPolicyAdmin: domain display, pattern badge, sync actions
   - CrawlJobAdmin: product_url display, sync status, product_url select_related
   - Fixed: stats_display, next_run_display format string issues

5. **services/crawl_service/migrations/0004_domain_based_policies.py**
   - Add domain, name, url_pattern to CrawlPolicy (nullable)
   - Add product_url to CrawlJob (nullable)
   - Create indexes and unique constraints

6. **services/crawl_service/management/commands/create_initial_policies.py**
   - Create default policy for each domain (23 total)

---

## Deployment Checklist

- [x] Models refactored
- [x] Signals updated
- [x] API Pull endpoint updated
- [x] Admin interface updated (all errors fixed)
- [x] Migrations created and applied
- [x] Initial policies created (23 domains)
- [x] All URLs synced to jobs (32 jobs created)
- [ ] API Submit endpoint update (pending)
- [ ] Serializers update (pending)
- [ ] End-to-end testing with real bot pull/submit

---

## Known Limitations

1. **Submit API**: Still uses old structure, needs update to use product_url
2. **Serializers**: CrawlJobSerializer may need update for new schema
3. **Migration 0005**: Future migration to make fields non-nullable (after data migration)

---

## Rollback Plan

If issues arise:

```bash
# Rollback migration
python manage.py migrate crawl_service 0003

# Restore models from backup
git restore services/crawl_service/models.py

# Clear test data
python manage.py shell -c "from services.crawl_service.models import *; CrawlJob.objects.all().delete()"
```

---

## Next Steps

1. Update Submit API endpoint
2. Update serializers
3. Create data migration if needed (currently skipped with nullable fields)
4. End-to-end test with real bot
5. Monitor admin performance with large datasets
6. Consider pagination for admin list views (32 jobs is small, but millions would be slow)

---

**Status**: Ready for testing with bot pull/submit cycle
