# Auto-Record Quick Reference

## Quick Start

1. **Enable auto-record:**
   - Go to Django Admin `/admin/{ADMIN_HASH}/crawl_service/`
   - Click **⚙️ Auto-Record Configuration** or navigate to `/admin/{ADMIN_HASH}/crawl_service/auto-record-config/`
   - Check **Enabled** checkbox
   - Click **Save**

2. **Configure criteria:**
   - **Allowed Sources:** Which extraction methods (jsonld, og, microdata, script_data, html_ml)
   - **Min ML Confidence:** 0.85 (if html_ml enabled)
   - **Require In Stock:** Check for in-stock only
   - **Allowed Domains:** Leave empty for all, or specify (amazon.jp, etc.)
   - **Currency Whitelist:** Leave empty for all, or specify (JPY, USD, etc.)

3. **Monitor:**
   - Go to Crawl Results list
   - Check "Auto-Record Status" in result detail
   - Look for ✓ or ✗ badge + reason

## Config File Location

`services/crawl_service/infrastructure/auto_record_config.json`

Default:
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

## How It Works

```
CrawlResult Created
    ↓
Signal Handler Triggered
    ↓
should_auto_record(result) checks:
  • Is auto-record enabled?
  • In stock (if required)?
  • Currency in whitelist (if set)?
  • Domain in whitelist (if set)?
  • Has allowed sources?
  • ML confidence >= min (if html_ml)?
    ↓
    YES: write_price_history_for_result()
         • Check for duplicate (latest price)
         • Create PriceHistory or mark duplicate
         • Update result.history_recorded_* fields
    ↓
    NO: result remains unrecorded
```

## Admin Features

### Crawl Results List
- **Recording** column shows: ✓ Recorded, ⎘ Duplicate, ✗ Failed, — Not Recorded
- **Filter by:** `history_record_status` (recorded, duplicate, failed, none)

### Crawl Results Detail
- **Auto-Record Status** section shows:
  - ✓ Meets auto-record criteria (green)
  - ✗ Does not meet criteria: [reasons] (red)
  - ⚙️ Auto-record DISABLED (gray)
- Manual action available: **🧾 Write price to shared history** (bulk override)

### Crawl Dashboard
- Auto-Record Configuration is accessible directly via URL: `/admin/{ADMIN_HASH}/crawl_service/auto-record-config/`
- Also available from CrawlResults detail view in "Auto-Record Status" fieldset

## Common Configurations

### Record all JPY prices (high ML confidence)
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

### Record structured data from specific shops
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

### Record everything (no restrictions)
```json
{
  "enabled": true,
  "allowed_sources": ["jsonld", "og", "microdata", "script_data", "html_ml"],
  "min_confidence": 0.0,
  "require_in_stock": false,
  "allowed_domains": [],
  "currency_whitelist": []
}
```

## Database Fields

CrawlResult tracking:
- `history_recorded`: Boolean (recorded to PriceHistory?)
- `history_record_status`: String (none, recorded, duplicate, failed)
- `history_recorded_at`: DateTime (when acknowledged)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Auto-record not working | Check `enabled: true` in config |
| Wrong results recorded | Review criteria in detail view (✗ badge explains why) |
| Getting duplicates | Expected! Latest price matched = duplicate mark |
| Config changes not applying | Refresh admin page; check file saved |

## Code Components

| Location | Purpose |
|----------|---------|
| `infrastructure/auto_recording.py` | get/save config, evaluate criteria, write history |
| `signals.py` | Signal handler triggered on CrawlResult creation |
| `admin/admin.py` | CrawlResultAdmin enhancements |
| `core/admin_core/infrastructure/custom_admin.py` | Admin config view & URL routing |
| `templates/admin/crawl_auto_record_config.html` | Config form template |

## Related Files

- Full guide: [AUTO_RECORD_GUIDE.md](./AUTO_RECORD_GUIDE.md)
- Crawl Service: [README.md](./README.md)
- Infrastructure: [infrastructure/auto_recording.py](./infrastructure/auto_recording.py)
