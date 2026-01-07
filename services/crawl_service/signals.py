"""
Django Signals for Crawl Service

Auto-create CrawlJob when new ProductURL is added.
Finds appropriate CrawlPolicy by domain (group-based, not per-URL).
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import logging

from services.products_shared.infrastructure.django_models import ProductURL
from services.crawl_service.models import CrawlPolicy, CrawlJob

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ProductURL)
def auto_create_crawl_job(sender, instance, created, **kwargs):
    """
    Automatically create CrawlJob when new ProductURL is added.
    
    Tìm CrawlPolicy phù hợp theo domain (không tạo policy mới cho mỗi URL).
    Scale tốt cho hàng triệu URLs.
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
            return
        
        # Tìm policy phù hợp cho domain này (priority cao nhất)
        policies = CrawlPolicy.objects.filter(
            domain=domain,
            enabled=True
        ).order_by('-priority')
        
        # Check pattern matching
        matching_policy = None
        for policy in policies:
            if policy.matches_url(instance.normalized_url):
                matching_policy = policy
                break
        
        if not matching_policy:
            logger.warning(
                f"No enabled CrawlPolicy found for domain={domain.name}, "
                f"URL will not be crawled: {instance.normalized_url[:80]}"
            )
            return
        
        # Check if job already exists for this URL
        existing_job = CrawlJob.objects.filter(
            product_url=instance,
            status__in=['pending', 'locked']
        ).exists()
        
        if existing_job:
            logger.info(f"Job already exists for: {instance.normalized_url[:80]}")
            return
        
        # Create CrawlJob
        job = CrawlJob.objects.create(
            policy=matching_policy,
            product_url=instance,
            status='pending',
            priority=matching_policy.priority,
            max_retries=matching_policy.max_retries,
            retry_count=0,
            lock_ttl_seconds=600,
        )
        
        logger.info(
            f"✓ Auto-created CrawlJob: {job.id} for {instance.normalized_url[:80]} "
            f"(policy={matching_policy.name})"
        )
            
    except Exception as e:
        logger.error(f"Failed to auto-create job for {instance.normalized_url[:80]}: {e}", exc_info=True)
