# Auto-Record Logic Fix Summary

## Issues Found & Fixed (January 12, 2026)

### 🐛 Bug #1: Strict Source Matching
**Issue:** Logic để check allowed sources bị hard-coded, dẫn đến nhiều CrawlResult đủ điều kiện nhưng không được ghi.

**Root Cause:**
```python
# OLD - ambiguous logic
allowed_sources = set(cfg.get('allowed_sources') or [])
if allowed_sources and not (set(sources) & allowed_sources):
    return False
```

**Problem:** Không rõ khi nào check apply:
- Set rỗng? → Bỏ qua check
- Set không rỗng? → Phải có intersection

**✅ Fixed:**
```python
# NEW - explicit logic
allowed_sources = cfg.get('allowed_sources') or []
if allowed_sources:
    if not (set(price_sources) & set(allowed_sources)):
        return False
# If allowed_sources is empty, ANY source is acceptable
```

---

### 🐛 Bug #2: Missing Debug Logs
**Issue:** Khi CrawlResult không meet criteria, không biết lý do tại sao.

**✅ Fixed:** Added detailed debug logs:
```python
logger.debug(f"Result {result.id}: No price sources found")
logger.debug(f"Result {result.id}: No allowed sources. Have: {price_sources}, Allowed: {allowed_sources}")
logger.debug(f"Result {result.id}: ML confidence {confidence} < {min_confidence}")
logger.debug(f"Result {result.id}: Price {price_float} is <= 0")
```

---

### 🐛 Bug #3: Price Validation
**Issue:** Check `== 0.0` nhưng không check negative prices.

**✅ Fixed:**
```python
# OLD
if float(result.price) == 0.0:
    return False

# NEW - more robust
if price_float <= 0.0:
    logger.debug(...)
    return False
```

---

### 🐛 Bug #4: Better Signal Logging
**Issue:** Signal handler không log khi config disabled.

**✅ Fixed:** Added explicit check:
```python
cfg = get_auto_record_config()
if not cfg.get('enabled'):
    logger.info(f"CrawlResult {result_id}: Auto-record disabled in config")
    return
```

---

## Files Modified

1. **`infrastructure/auto_recording.py`**
   - Rewrote `should_auto_record()` logic
   - Added debug logging for each failing condition
   - Better error handling

2. **`signals.py`**
   - Improved logging clarity
   - Added config check at signal start
   - Better exception handling

---

## Testing the Fix

### Quick Test
```bash
cd /var/www/PriceSynC/Saas_app

# 1. Check config
python manage.py shell
>>> from services.crawl_service.infrastructure.auto_recording import get_auto_record_config
>>> cfg = get_auto_record_config()
>>> print(cfg)

# 2. Test should_auto_record on a CrawlResult
>>> from services.crawl_service.models import CrawlResult
>>> from services.crawl_service.infrastructure.auto_recording import should_auto_record
>>> result = CrawlResult.objects.latest('created_at')
>>> print(should_auto_record(result))

# 3. Check logs for debug info
# Look for: logger.debug messages explaining why passed/failed
```

### Full Debugging Guide
See: [AUTO_RECORD_DEBUGGING.md](./AUTO_RECORD_DEBUGGING.md)

---

## Current Config

```json
{
  "enabled": true,
  "allowed_sources": ["html_ml"],
  "min_confidence": 0.85,
  "require_in_stock": false,
  "allowed_domains": [],
  "currency_whitelist": []
}
```

**Means:**
- ✅ Auto-record ON
- ✅ MUST have `html_ml` in price_sources
- ✅ MUST have ML confidence >= 0.85
- ⊘ Stock check OFF
- ⊘ Domain filter OFF
- ⊘ Currency filter OFF

---

## Expected Behavior After Fix

### ✅ Will Auto-Record
CrawlResult with:
- `price_sources`: `['html_ml']`
- ML confidence: `0.95`
- Price: `99.99`

### ❌ Won't Auto-Record
- `price_sources`: `['jsonld']` (no html_ml)
- `price_sources`: `['html_ml']`, confidence: `0.70` (< 0.85)
- Price: `0.0` or `None`

---

## Documentation

- [Quick Reference](./AUTO_RECORD_QUICK_REFERENCE.md)
- [Full Guide](./AUTO_RECORD_GUIDE.md)
- [Implementation Details](./AUTO_RECORD_IMPLEMENTATION.md)
- **[Debugging Guide](./AUTO_RECORD_DEBUGGING.md)** ← Use this to troubleshoot

