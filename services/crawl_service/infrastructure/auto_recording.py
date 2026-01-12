import json
import os
import logging
from typing import Dict, Any

from django.utils import timezone

logger = logging.getLogger(__name__)

# Config file path (repo-local; ensure writable by app user)
CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    'auto_record_config.json'
)

DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "allowed_sources": ["jsonld", "og", "microdata", "script_data", "html_ml"],
    "min_confidence": 0.85,  # applies to html_ml only
    "require_in_stock": True,
    "allowed_domains": [],  # empty → any
    "currency_whitelist": [],  # empty → any
    "_cron_config": {
        "_comment": "DO NOT DELETE: Cron configuration for auto-record scheduler",
        "scheduler_enabled": True,
        "interval_seconds": 30,
        "batch_size": 100,
        "max_retries": 3,
        "retry_failed_every_n_cycles": 50,
        "retry_failed_limit": 20,
        "log_queue_status_every_n_cycles": 10,
    }
}


def get_auto_record_config() -> Dict[str, Any]:
    """
    Load auto-record config from JSON file with sane defaults.
    
    Auto-repairs config file if _cron_config is missing.
    """
    try:
        if not os.path.exists(CONFIG_PATH):
            save_auto_record_config(DEFAULT_CONFIG.copy())
            return DEFAULT_CONFIG.copy()
        
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # merge defaults for missing keys
            merged = DEFAULT_CONFIG.copy()
            merged.update(data or {})
            
            # Auto-repair if _cron_config missing in file
            if '_cron_config' not in data:
                logger.warning("_cron_config missing from config file - auto-repairing")
                save_auto_record_config(merged)
            
            return merged
            
    except Exception as e:
        logger.error(f"Failed to load auto record config: {e}")
        return DEFAULT_CONFIG.copy()


def save_auto_record_config(data: Dict[str, Any]) -> None:
    """
    Persist config to JSON file.
    
    IMPORTANT: Preserves _cron_config structure to prevent deletion on save.
    """
    try:
        # Build config keeping both criteria and cron settings
        cfg = DEFAULT_CONFIG.copy()
        
        # Update main config keys
        for key in ['enabled', 'allowed_sources', 'min_confidence', 'require_in_stock', 'allowed_domains', 'currency_whitelist']:
            if key in data:
                cfg[key] = data[key]
        
        # Preserve _cron_config if provided, else use default
        if '_cron_config' in data and isinstance(data['_cron_config'], dict):
            cfg['_cron_config'] = data['_cron_config']
        
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved auto-record config: enabled={cfg['enabled']}, scheduler_enabled={cfg.get('_cron_config', {}).get('scheduler_enabled', 'N/A')}")
            
    except Exception as e:
        logger.error(f"Failed to save auto record config: {e}", exc_info=True)


def should_auto_record(result) -> bool:
    """Evaluate whether a CrawlResult meets auto-record conditions.

    Criteria sourced from parsed_data, stock, domain, and currency.
    """
    cfg = get_auto_record_config()
    if not cfg.get('enabled'):
        return False

    try:
        # Stock requirement
        if cfg.get('require_in_stock', True) and not bool(result.in_stock):
            return False

        # Currency whitelist check
        currency_whitelist = cfg.get('currency_whitelist') or []
        if currency_whitelist:  # Only check if whitelist is not empty
            if (result.currency or '').upper() not in {c.upper() for c in currency_whitelist}:
                return False

        # Domain whitelist check
        domain_whitelist = cfg.get('allowed_domains') or []
        if domain_whitelist:  # Only check if whitelist is not empty
            domain_name = None
            try:
                domain_name = result.job.product_url.domain.name if result.job and result.job.product_url else None
            except Exception as e:
                logger.debug(f"Failed to get domain name: {e}")
                domain_name = None
            
            if not domain_name or domain_name not in domain_whitelist:
                return False

        # Parse and check price sources
        parsed_data = result.parsed_data or {}
        price_sources = parsed_data.get('price_sources') or []
        
        # If no sources in parsed_data, cannot auto-record
        if not price_sources:
            logger.debug(f"Result {result.id}: No price sources found in parsed_data")
            return False

        # Check allowed sources
        allowed_sources = cfg.get('allowed_sources') or []
        if allowed_sources:  # Only check if list is not empty
            # Must have at least one source from allowed list
            source_intersection = set(price_sources) & set(allowed_sources)
            if not source_intersection:
                logger.debug(f"Result {result.id}: No allowed sources found. Have: {price_sources}, Allowed: {allowed_sources}")
                return False
        
        # If no allowed sources configured, any source is acceptable
        # (as long as it exists, which we already checked above)

        # ML confidence check - only if html_ml is in the sources
        if 'html_ml' in price_sources:
            price_extraction = parsed_data.get('price_extraction') or {}
            ml_data = price_extraction.get('extract_price_from_html_ml') or {}
            confidence = float(ml_data.get('confidence') or 0.0)
            min_confidence = float(cfg.get('min_confidence') or 0.85)
            
            if confidence < min_confidence:
                logger.debug(f"Result {result.id}: ML confidence {confidence} < {min_confidence}")
                return False

        # Price must exist and be non-zero
        if result.price is None:
            logger.debug(f"Result {result.id}: Price is None")
            return False
        
        try:
            price_float = float(result.price)
            if price_float <= 0.0:
                logger.debug(f"Result {result.id}: Price {price_float} is <= 0")
                return False
        except (ValueError, TypeError) as e:
            logger.debug(f"Result {result.id}: Invalid price value: {e}")
            return False

        # All checks passed
        logger.debug(f"Result {result.id}: ✓ Meets all auto-record criteria")
        return True
        
    except Exception as e:
        logger.error(f"Auto-record evaluation error for result {getattr(result, 'id', '?')}: {e}", exc_info=True)
        return False


def write_price_history_for_result(result) -> bool:
    """Write shared PriceHistory entry from a CrawlResult and update recording flags.

    Returns True when a new entry was created, False if duplicate (acknowledged).
    """
    try:
        from services.products_shared.infrastructure.django_models import PriceHistory

        if not result.job or not result.job.product_url:
            return False

        product_url = result.job.product_url
        new_price = result.price
        currency = result.currency or 'JPY'
        is_available = bool(result.in_stock)
        scraped_at = result.crawled_at or timezone.now()

        # Duplicate detection against latest
        last = PriceHistory.objects.filter(product_url=product_url).order_by('-scraped_at').first()
        if last is not None and last.price == new_price:
            result.history_recorded = True
            result.history_record_status = 'duplicate'
            result.history_recorded_at = scraped_at
            result.save(update_fields=['history_recorded', 'history_record_status', 'history_recorded_at'])
            return False

        PriceHistory.objects.create(
            product_url=product_url,
            price=new_price,
            currency=currency,
            original_price=None,
            is_available=is_available,
            stock_status='',
            stock_quantity=None,
            source='AUTO',
            scraped_at=scraped_at,
        )
        result.history_recorded = True
        result.history_record_status = 'recorded'
        result.history_recorded_at = scraped_at
        result.save(update_fields=['history_recorded', 'history_record_status', 'history_recorded_at'])
        return True
    except Exception as e:
        logger.error(f"Failed to auto write price history for result {getattr(result, 'id', '?')}: {e}")
        try:
            result.history_recorded = False
            result.history_record_status = 'failed'
            result.history_recorded_at = timezone.now()
            result.save(update_fields=['history_recorded', 'history_record_status', 'history_recorded_at'])
        except Exception:
            pass
        return False
