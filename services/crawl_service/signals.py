"""
Django Signals for Crawl Service

Auto-create CrawlJob when new ProductURL is added.
Status resets are handled via Redis-backed JobResetRule; no policy selection.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import logging

from services.products_shared.infrastructure.django_models import ProductURL
from services.crawl_service.models import CrawlJob, JobResetRule
from services.crawl_service.infrastructure.redis_job_scheduler import schedule_reset_to_pending

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ProductURL)
def auto_create_crawl_job(sender, instance, created, **kwargs):
    """
    Automatically create CrawlJob when new ProductURL is added.
    
    Create jobs with default configuration; policy selection removed.
    """
    if not created:
        return  # Only for new URLs
    
    if not instance.is_active:
        logger.info(f"Skipping inactive ProductURL: {instance.normalized_url[:80]}")
        return
    
    try:
        domain = instance.domain
        if not domain:
            logger.warning(f"ProductURL has no domain: {instance.normalized_url[:80]}")
        
        # Policy no longer determines creation; create job with defaults
        
        # Check if job already exists for this URL
        existing_job = CrawlJob.objects.filter(
            product_url=instance,
            status__in=['pending', 'locked']
        ).exists()
        
        if existing_job:
            logger.info(f"Job already exists for: {instance.normalized_url[:80]}")
            return
        
        # Create CrawlJob with defaults
        job = CrawlJob.objects.create(
            product_url=instance,
            status='pending',
            priority=5,
            max_retries=3,
            retry_count=0,
            timeout_minutes=10,
            lock_ttl_seconds=600,
            rule_tag='base',
        )
        
        logger.info(
            f"✓ Auto-created CrawlJob: {job.id} for {instance.normalized_url[:80]}"
        )
            
    except Exception as e:
        logger.error(f"Failed to auto-create job for {instance.normalized_url[:80]}: {e}", exc_info=True)


@receiver(post_save, sender=JobResetRule)
def apply_rule_on_save(sender, instance: JobResetRule, created, **kwargs):
    """
    When a JobResetRule is saved, schedule resets:
    - Enqueue DONE jobs matching the rule to become PENDING.
    """
    try:
        if not instance.enabled:
            return

        # Build queryset of matching jobs (DONE only to avoid locking/pending noise)
        qs = CrawlJob.objects.filter(status='done')
        sel = instance.SelectionType
        if instance.selection_type == sel.DOMAIN and instance.domain:
            qs = qs.filter(product_url__domain=instance.domain)
        elif instance.selection_type == sel.DOMAIN_REGEX and instance.domain_regex:
            qs = qs.filter(product_url__domain__name__regex=instance.domain_regex)
        elif instance.selection_type == sel.URL_REGEX and instance.url_pattern:
            qs = qs.filter(product_url__normalized_url__regex=instance.url_pattern)
        elif instance.selection_type == sel.RULE and instance.rule_tag:
            qs = qs.filter(rule_tag=instance.rule_tag)
        # ALL → leave qs as-is

        job_ids = list(qs.values_list('id', flat=True)[:1000])  # cap batch
        if not job_ids:
            return

        run_at = timezone.now().timestamp()  # immediate reset
        scheduled = schedule_reset_to_pending([str(jid) for jid in job_ids], run_at_ts=run_at)
        logger.info(
            f"Rule '{instance.name}' scheduled {scheduled} DONE jobs to PENDING via Redis"
        )
    except Exception as e:
        logger.error(f"apply_policy_on_save error: {e}")


# Auto-record CrawlResult to url-price when config conditions are met
@receiver(post_save, sender='crawl_service.CrawlResult')
def auto_record_crawl_result(sender, instance, created, **kwargs):
    """
    Enqueue CrawlResult for async auto-recording.
    
    Does NOT block on record write - just enqueues to Redis.
    Actual recording happens asynchronously via scheduler.
    
    Only runs on creation (not update).
    """
    if not created:
        return  # Only for new results
    
    try:
        from services.crawl_service.infrastructure.auto_recording import get_auto_record_config
        from services.crawl_service.infrastructure.auto_record_queue import enqueue_auto_record
        
        cfg = get_auto_record_config()
        result_id = getattr(instance, 'id', '?')
        
        # Check if auto-record is enabled
        if not cfg.get('enabled'):
            logger.debug(f"CrawlResult {result_id}: Auto-record disabled in config")
            return
        
        # Enqueue for async processing (non-blocking)
        if enqueue_auto_record(str(result_id)):
            logger.debug(f"✓ Enqueued CrawlResult {result_id} for auto-record processing")
        else:
            logger.warning(f"✗ Failed to enqueue CrawlResult {result_id} for auto-record")
            
    except Exception as e:
        logger.error(f"✗ Auto-record signal failed for result {getattr(instance, 'id', '?')}: {e}", exc_info=True)
