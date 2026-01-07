import logging
from typing import Optional
from datetime import datetime

from django.db import transaction

from services.crawl_service.models import CrawlJob, ScheduleRule
from services.products_shared.infrastructure.django_models import ProductURL, Domain

logger = logging.getLogger(__name__)


def create_jobs_from_shared(
    schedule_rule_id: str,
    domain_name: Optional[str] = None,
    limit: Optional[int] = None,
    only_active: bool = True,
    use_normalized_url: bool = True,
) -> int:
    """
    Create CrawlJob entries from shared ProductURL records.

    Args:
        schedule_rule_id: UUID of ScheduleRule to assign to jobs
        domain_name: Optional domain filter (e.g., 'amazon.co.jp')
        limit: Optional maximum number of URLs to import
        only_active: If True, import only active ProductURL entries
        use_normalized_url: Use normalized_url instead of raw_url if available

    Returns:
        Number of jobs created
    """
    try:
        rule = ScheduleRule.objects.get(id=schedule_rule_id)
    except ScheduleRule.DoesNotExist:
        raise ValueError("ScheduleRule not found")

    qs = ProductURL.objects.all().select_related('domain')
    if only_active:
        qs = qs.filter(is_active=True)
    if domain_name:
        try:
            domain = Domain.objects.get(name=domain_name)
            qs = qs.filter(domain=domain)
        except Domain.DoesNotExist:
            raise ValueError(f"Domain not found: {domain_name}")

    if limit:
        qs = qs[:int(limit)]

    created = 0
    now = datetime.now()

    with transaction.atomic():
        for pu in qs:
            url = pu.normalized_url if use_normalized_url and pu.normalized_url else pu.raw_url
            if not url:
                continue
            # Avoid duplicates by unique url constraint
            obj, was_created = CrawlJob.objects.get_or_create(
                url=url,
                defaults={
                    'status': 'pending',
                    'schedule_rule': rule,
                    'priority': rule.priority,
                    'max_retries': rule.max_retries,
                    'timeout_minutes': rule.timeout_minutes,
                    'next_run_at': now,
                }
            )
            if was_created:
                created += 1

    logger.info(
        "Imported %s jobs from shared products (domain=%s, limit=%s, only_active=%s)",
        created, domain_name, limit, only_active,
    )
    return created
