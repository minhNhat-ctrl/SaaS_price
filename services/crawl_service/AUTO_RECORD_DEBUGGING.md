# Auto-Record Logic Fix - Debugging Guide

## Issues Found & Fixed

### 1. ❌ Logic Bug: Strict Source Checking
**Problem:** 
```python
allowed_sources = set(cfg.get('allowed_sources') or [])
if allowed_sources and not (set(sources) & allowed_sources):
    return False
```

This would ALWAYS reject if config has allowed_sources list but no intersection found.

**✅ Fixed:**
```python
allowed_sources = cfg.get('allowed_sources') or []
if allowed_sources:  # Only check if list is not empty
    source_intersection = set(price_sources) & set(allowed_sources)
    if not source_intersection:
        logger.debug(...)
        return False
```

Key difference: Now it's clear when the check applies:
- **If allowed_sources list is NOT empty** → Must have intersection
- **If allowed_sources list IS empty** → ANY source is acceptable

---

### 2. ❌ Logic Bug: Currency/Domain Whitelists
**Problem:**
```python
cwl = cfg.get('currency_whitelist') or []
if cwl and (result.currency or '').upper() not in {c.upper() for c in cwl}:
```

Same issue - wasn't clear when check applies.

**✅ Fixed:**
```python
currency_whitelist = cfg.get('currency_whitelist') or []
if currency_whitelist:  # Only check if whitelist is not empty
    if (result.currency or '').upper() not in {c.upper() for c in currency_whitelist}:
        return False
```

---

### 3. ❌ Missing Debug Information
**Problem:** When criteria failed, no debug logs explaining why.

**✅ Fixed:** Added detailed debug logs:
```python
logger.debug(f"Result {result.id}: No price sources found in parsed_data")
logger.debug(f"Result {result.id}: No allowed sources found. Have: {price_sources}, Allowed: {allowed_sources}")
logger.debug(f"Result {result.id}: ML confidence {confidence} < {min_confidence}")
logger.debug(f"Result {result.id}: Price {price_float} is <= 0")
```

---

### 4. ❌ Price Check: Zero vs None
**Problem:**
```python
if float(result.price) == 0.0:
    return False
```

Should be `<= 0` to also catch negative prices.

**✅ Fixed:**
```python
if price_float <= 0.0:
    logger.debug(...)
    return False
```

---

## Config Behavior Explained

Current config:
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

**Criteria for auto-record:**
1. ✓ enabled = true
2. ✓ Price source must include `html_ml` (since allowed_sources is not empty)
3. ✓ If html_ml present, confidence >= 0.85
4. ✓ Stock check SKIPPED (require_in_stock = false)
5. ✓ Domain check SKIPPED (allowed_domains = [])
6. ✓ Currency check SKIPPED (currency_whitelist = [])
7. ✓ Price must be > 0

---

## Debugging Steps

### Step 1: Check Config is Enabled
```bash
cd /var/www/PriceSynC/Saas_app
python manage.py shell
```

```python
from services.crawl_service.infrastructure.auto_recording import get_auto_record_config
cfg = get_auto_record_config()
print(cfg)
```

Expected output:
```
{
  "enabled": true,
  "allowed_sources": ["html_ml"],
  "min_confidence": 0.85,
  "require_in_stock": false,
  "allowed_domains": [],
  "currency_whitelist": []
}
```

### Step 2: Test should_auto_record() on a Result
```python
from services.crawl_service.models import CrawlResult
from services.crawl_service.infrastructure.auto_recording import should_auto_record

result = CrawlResult.objects.latest('created_at')
print(f"Result ID: {result.id}")
print(f"Price: {result.price}")
print(f"In Stock: {result.in_stock}")
print(f"Parsed Data: {result.parsed_data}")
print(f"Should auto-record: {should_auto_record(result)}")
```

Check the logs for detailed reason why it passed/failed:
```bash
tail -f /var/log/django/crawl_service.log
```

### Step 3: Check Parsed Data Structure
```python
result = CrawlResult.objects.latest('created_at')
pd = result.parsed_data or {}
print(f"Price Sources: {pd.get('price_sources')}")
print(f"Price Extraction: {pd.get('price_extraction')}")

# Check ML confidence if html_ml present
if 'html_ml' in (pd.get('price_sources') or []):
    ml_data = pd.get('price_extraction', {}).get('extract_price_from_html_ml', {})
    print(f"ML Confidence: {ml_data.get('confidence')}")
```

### Step 4: Create Test CrawlResult
To test with a known good result:

```python
from services.crawl_service.models import CrawlJob, CrawlResult
from services.products_shared.infrastructure.django_models import ProductURL
from decimal import Decimal
from django.utils import timezone
import json

# Find a job
job = CrawlJob.objects.filter(status='done').first()

# Create result with known good data
result = CrawlResult.objects.create(
    job=job,
    price=Decimal('99.99'),
    currency='JPY',
    title='Test Product',
    in_stock=True,
    crawled_at=timezone.now(),
    parsed_data={
        'price_sources': ['html_ml'],
        'price_extraction': {
            'extract_price_from_html_ml': {
                'confidence': 0.95
            }
        }
    }
)

print(f"Created result: {result.id}")
```

Then check logs:
```bash
# Should see: "✓ Auto-recorded CrawlResult ... to PriceHistory"
tail -f /var/log/django/crawl_service.log
```

---

## Expected Log Output

### ✅ Successful Auto-Record
```
[crawl_service] Result abc123: ✓ Meets all auto-record criteria
[crawl_service] ✓ Auto-recorded CrawlResult abc123 to PriceHistory
```

### ❌ Failed - No html_ml Source
```
[crawl_service] Result def456: No allowed sources found. Have: ['jsonld'], Allowed: ['html_ml']
```

### ❌ Failed - Low ML Confidence
```
[crawl_service] Result ghi789: ML confidence 0.72 < 0.85
```

### ❌ Failed - Invalid Price
```
[crawl_service] Result jkl012: Price 0.0 is <= 0
```

### ⚠️ Duplicate Price
```
[crawl_service] ~ CrawlResult mno345: Recorded attempt (duplicate or handled)
```

---

## Common Issues & Solutions

### Issue: Auto-record not working
**Check:**
1. Is `enabled: true` in config?
2. Are CrawlResults being created? (Check DB)
3. Look at Django logs for signal errors
4. Run step 2 above to test should_auto_record()

### Issue: Some results auto-record, others don't
**Check:**
1. `parsed_data` structure - does it have `price_sources`?
2. `price_sources` includes `html_ml`?
3. If html_ml present, check `price_extraction.extract_price_from_html_ml.confidence`
4. Run debugging step 3 above

### Issue: Getting duplicates
**This is normal:**
- When `last_price == new_price` for same product_url
- Result marked as `history_record_status = 'duplicate'`
- This is intentional to avoid duplicate price entries

### Issue: Config changes not applying
**Solution:**
1. Check file saved: `cat auto_record_config.json`
2. Reload Django: `systemctl restart gunicorn-saas.service`
3. Test again: `python manage.py shell` + run step 1

---

## Code Changes Summary

| File | Changes |
|------|---------|
| `infrastructure/auto_recording.py` | Fixed should_auto_record() logic, added debug logging |
| `signals.py` | Improved logging, added config check |

**Key improvements:**
- ✅ Clearer logic for empty vs non-empty lists
- ✅ Detailed debug logs for each failing condition
- ✅ Better error handling and information
- ✅ Price check now includes negative values

