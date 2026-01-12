# Auto-Record Crawl Results to URL-Price

## Overview

The Auto-Record feature automatically writes `CrawlResult` entries to shared `PriceHistory` when certain conditions are met. This eliminates the need for manual recording via admin actions and ensures consistent, conditional price tracking.

**Key Benefits:**
- ✅ Automatic price recording based on configurable criteria
- ✅ Avoids duplicate price entries (duplicate detection via latest price)
- ✅ Conditional recording: source, ML confidence, stock status, domain, currency
- ✅ Transparent evaluation in admin UI
- ✅ Easy-to-use Django admin interface for configuration

---

## Architecture

### File-Based Configuration

Config is stored in **`services/crawl_service/infrastructure/auto_record_config.json`** (not in database).

**Why file-based?**
- Simple, no migrations needed
- Easy to version control
- Can be deployed via environment-specific configs
- Works with CI/CD pipelines

**Default Config:**
```json
{
  "enabled": false,
  "allowed_sources": ["jsonld", "og", "microdata", "script_data", "html_ml"],
  "min_confidence": 0.85,
  "require_in_stock": true,
  "allowed_domains": [],
  "currency_whitelist": []
}
```

### Data Flow

```
CrawlResult created
    ↓
post_save signal triggered
    ↓
auto_record_crawl_result() signal handler
    ↓
should_auto_record(result) checks criteria
    ├─ Config enabled?
    ├─ Stock requirement met?
    ├─ Currency whitelisted?
    ├─ Domain allowed?
    ├─ Sources present & allowed?
    └─ ML confidence >= min?
    ↓
write_price_history_for_result()
    ├─ Check for duplicate (latest price)
    ├─ Create PriceHistory entry or mark duplicate
    └─ Update recording flags
```

### Components

#### 1. **Infrastructure Layer** (`infrastructure/auto_recording.py`)
- `get_auto_record_config()` - Load config from JSON
- `save_auto_record_config(data)` - Persist config to JSON
- `should_auto_record(result)` - Evaluate if result meets criteria
- `write_price_history_for_result(result)` - Write to PriceHistory

#### 2. **Signals** (`signals.py`)
- `auto_record_crawl_result()` - Post-save signal on CrawlResult
  - Only runs on creation (not updates)
  - Automatically calls write_price_history_for_result if criteria met
  - Logs success/failure

#### 3. **Admin Interface** (`core/admin_core/infrastructure/custom_admin.py`)
- `auto_record_config_view()` - GET/POST handler
  - GET: Display config form
  - POST: Save updated config
- URL: `/admin/{ADMIN_HASH}/crawl/auto-record-config/`

#### 4. **Admin UI Enhancements** (`services/crawl_service/admin/admin.py`)
- `CrawlResultAdmin.auto_record_status_display` - Show evaluation result
  - ✓ Meets auto-record criteria
  - ✗ Does not meet criteria + reason
  - ⚙️ Auto-record disabled
- Link in Crawl Dashboard to config view

---

## Configuration Guide

### Access Config Interface

1. Navigate to Django Admin config view: `/admin/{ADMIN_HASH}/crawl_service/auto-record-config/`
2. Or go to CrawlResults list → open any result detail → scroll to "Auto-Record Status" section
3. Modify settings and click **Save**

### Configuration Options

#### **Enabled**
- **Type:** Boolean (checkbox)
- **Default:** `false`
- **Purpose:** Master switch. When disabled, no auto-recording happens regardless of other settings.

#### **Allowed Sources**
- **Type:** CSV list
- **Default:** `jsonld, og, microdata, script_data, html_ml`
- **Purpose:** Which price extraction sources are acceptable
- **Example:** `jsonld, og` (only accept these sources)
- **Note:** Result must have at least one source from this list

#### **Min ML Confidence**
- **Type:** Float (0.0 - 1.0)
- **Default:** `0.85`
- **Purpose:** Minimum confidence threshold for ML-extracted prices
- **Only applies:** When `html_ml` is in result's price_sources
- **Example:** `0.90` requires very high confidence

#### **Require In Stock**
- **Type:** Boolean (checkbox)
- **Default:** `true`
- **Purpose:** Only record prices for in-stock products
- **When unchecked:** Records out-of-stock prices too

#### **Allowed Domains**
- **Type:** CSV list
- **Default:** Empty (all domains allowed)
- **Purpose:** Restrict recording to specific domains
- **Example:** `amazon.jp, rakuten.co.jp` (only these domains)
- **Note:** Leave empty to allow any domain

#### **Currency Whitelist**
- **Type:** CSV list of ISO 4217 codes
- **Default:** Empty (all currencies allowed)
- **Purpose:** Only record prices in specific currencies
- **Example:** `JPY, USD, EUR`
- **Note:** Leave empty to allow any currency; codes are case-insensitive

---

## Examples

### Example 1: Record all JPY prices with high ML confidence

```json
{
  "enabled": true,
  "allowed_sources": ["html_ml"],
  "min_confidence": 0.95,
  "require_in_stock": true,
  "allowed_domains": [],
  "currency_whitelist": ["JPY"]
}
```

**Result:** Only ML-extracted JPY prices with ≥95% confidence from in-stock products are recorded.

### Example 2: Record structured data from specific domains only

```json
{
  "enabled": true,
  "allowed_sources": ["jsonld", "og", "microdata"],
  "min_confidence": 0.85,
  "require_in_stock": true,
  "allowed_domains": ["amazon.jp", "rakuten.co.jp"],
  "currency_whitelist": ["JPY"]
}
```

**Result:** Only structured-data prices from Amazon JP and Rakuten (in stock, JPY only).

### Example 3: Record all sources except ML (for testing)

```json
{
  "enabled": true,
  "allowed_sources": ["jsonld", "og", "microdata", "script_data"],
  "min_confidence": 0.85,
  "require_in_stock": false,
  "allowed_domains": [],
  "currency_whitelist": []
}
```

**Result:** Any non-ML source is recorded (even out-of-stock, any currency/domain).

### Example 4: Disabled auto-record (default)

```json
{
  "enabled": false,
  "allowed_sources": ["jsonld", "og", "microdata", "script_data", "html_ml"],
  "min_confidence": 0.85,
  "require_in_stock": true,
  "allowed_domains": [],
  "currency_whitelist": []
}
```

**Result:** Auto-recording is OFF. Manual recording via admin action still available.

---

## Admin UI: Crawl Results List

Each CrawlResult now shows:

### List Display
- **Recording** badge: `✓ Recorded` | `⎘ Duplicate` | `✗ Failed` | `— Not Recorded`

### Detail View: Auto-Record Status Section
- **✓ Meets auto-record criteria** - Green badge
  - If enabled, this result was auto-recorded
- **✗ Does not meet criteria: [reasons]** - Red badge
  - Examples: "Not in stock; Currency not whitelisted"
- **⚙️ Auto-record DISABLED** - Gray badge
  - Config has `enabled: false`

---

## Manual Recording Still Available

The existing `write_price_to_shared_history` bulk action is still available:

1. Select CrawlResults in list
2. Choose action: **🧾 Write price to shared history**
3. Click **Go**

This allows manual override/force-recording even if auto-record criteria aren't met.

---

## Recording Status Tracking

Each CrawlResult tracks recording attempts via:

| Field | Type | Purpose |
|-------|------|---------|
| `history_recorded` | Boolean | Whether recorded to PriceHistory |
| `history_record_status` | String | `none`, `recorded`, `duplicate`, `failed` |
| `history_recorded_at` | DateTime | When recording was acknowledged |

### Status Values
- **`none`** - Not yet recorded (auto-record disabled or didn't meet criteria)
- **`recorded`** - Successfully created new PriceHistory entry
- **`duplicate`** - Duplicate detected; not recorded (latest price matched)
- **`failed`** - Recording attempt failed (error)

---

## Monitoring & Debugging

### Check Auto-Record Status
1. Go to Crawl Results list
2. Open a result detail
3. Scroll to **Auto-Record Status** section
4. See: "✓ Meets auto-record criteria" or reason why not

### Monitor Recording Activity
1. Filter by `history_record_status`:
   - `recorded` - Successfully recorded
   - `duplicate` - Duplicate prevented
   - `failed` - Errors during recording
2. Check `history_recorded_at` timestamps

### View Logs
Check Django logs for signals:
```
[crawl_service] ✓ Auto-recorded CrawlResult <uuid> to PriceHistory
[crawl_service] CrawlResult <uuid> recorded (duplicate or failed)
[crawl_service] Auto-record signal failed for result <uuid>: <error>
```

---

## Use Cases

### Use Case 1: E-commerce Price Tracking
**Goal:** Track prices for specific high-value items

```json
{
  "enabled": true,
  "allowed_sources": ["jsonld", "og"],
  "min_confidence": 0.90,
  "require_in_stock": true,
  "allowed_domains": ["amazon.jp", "rakuten.co.jp", "yahoo.co.jp"],
  "currency_whitelist": ["JPY"]
}
```

### Use Case 2: ML Model Confidence Testing
**Goal:** Test ML extraction with high confidence threshold

```json
{
  "enabled": true,
  "allowed_sources": ["html_ml"],
  "min_confidence": 0.95,
  "require_in_stock": true,
  "allowed_domains": [],
  "currency_whitelist": []
}
```

### Use Case 3: Aggregated Price History
**Goal:** Record all extracted prices (with fallbacks)

```json
{
  "enabled": true,
  "allowed_sources": ["jsonld", "og", "microdata", "script_data", "html_ml"],
  "min_confidence": 0.70,
  "require_in_stock": false,
  "allowed_domains": [],
  "currency_whitelist": []
}
```

---

## API/Developer Notes

### Signal Handler
```python
@receiver(post_save, sender='crawl_service.CrawlResult')
def auto_record_crawl_result(sender, instance, created, **kwargs):
    # Only runs on creation
    if not should_auto_record(instance):
        return
    write_price_history_for_result(instance)
```

### Evaluation Function
```python
def should_auto_record(result) -> bool:
    cfg = get_auto_record_config()
    if not cfg.get('enabled'):
        return False
    # ... check stock, currency, domain, sources, confidence
    return True
```

### Writing Price History
```python
def write_price_history_for_result(result) -> bool:
    # Check for duplicate against latest
    if duplicate_detected:
        mark_as_duplicate()
        return False
    
    # Create new entry
    PriceHistory.objects.create(...)
    mark_as_recorded()
    return True
```

---

## FAQ

**Q: Why not use database models for config?**
A: File-based is simpler, version-controllable, and easier to manage in CI/CD.

**Q: Can I have different configs for different tenants?**
A: Currently one global config. Future: Support per-tenant configs via environment variables or separate files.

**Q: What happens to old manual recordings?**
A: They remain unchanged. Auto-record only processes new CrawlResults created after enabling.

**Q: Can I disable auto-record but keep the infrastructure?**
A: Yes, set `enabled: false` in config. Manual recording still works.

**Q: Does auto-record affect performance?**
A: Signal runs post-save, minimal impact. CPU-bound: criteria checking is fast.

---

## Troubleshooting

### Auto-Record Not Working
1. ✓ Check `enabled: true` in config
2. ✓ Check crawl result meets all criteria (see detail view)
3. ✓ Check Django logs for signal errors
4. ✓ Verify `CrawlResult` was created (not updated)

### Getting Duplicates
1. Check latest `PriceHistory` for this product
2. If price matches, marked as duplicate (expected)
3. To force-record: Use manual action `write_price_to_shared_history`

### Config Changes Not Applied
1. Refresh admin page
2. Check JSON file was saved (check file timestamps)
3. Restart Django (if using file caching)

---

## Related Documentation

- [Crawl Service README](./README.md)
- [Bot Developer Guide](./BOT_DEVELOPER_GUIDE.md)
- [Products Module](../products/)
