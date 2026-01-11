"""
Redis-backed job status scheduler.

Purpose:
- Schedule resetting `CrawlJob.status` back to 'pending' at specific times
- Process due resets without manual scheduler commands

Integration points:
- Called from API pull endpoint before serving jobs
- Called after successful submit to schedule next reset per policy frequency
"""

from __future__ import annotations

import time
import logging
from typing import Iterable

from django.utils import timezone

from .redis_adapter import get_cache_service
from ..models import CrawlJob

logger = logging.getLogger(__name__)


SCHEDULE_ZSET = "crawl:job_status_reset:zset"


def schedule_reset_to_pending(job_ids: Iterable[str], run_at_ts: float) -> int:
    """Schedule job IDs to be marked 'pending' at Unix timestamp run_at_ts.

    Returns number of jobs scheduled.
    """
    cache = get_cache_service()
    client = getattr(cache, "_client", None)
    if not client:
        logger.warning("Redis not available; skipping schedule reset")
        return 0

    try:
        # Use pipeline + ZADD with scores = run_at_ts
        pipe = client.pipeline()
        count = 0
        for jid in job_ids:
            pipe.zadd(SCHEDULE_ZSET, {str(jid): float(run_at_ts)})
            count += 1
        pipe.execute()
        return count
    except Exception as e:
        logger.error(f"Failed scheduling resets: {e}")
        return 0


def process_due_resets(max_batch: int = 500) -> int:
    """Process due status resets: mark jobs 'pending' whose schedule is due.

    Returns number of jobs reset.
    """
    cache = get_cache_service()
    client = getattr(cache, "_client", None)
    if not client:
        return 0

    now_ts = time.time()
    try:
        # Fetch due job ids
        job_ids = client.zrangebyscore(SCHEDULE_ZSET, min=0, max=now_ts, start=0, num=max_batch)
        if not job_ids:
            return 0

        # Update DB statuses for these jobs
        # Only reset jobs currently in DONE or FAILED/EXPIRED back to PENDING
        updated = CrawlJob.objects.filter(id__in=job_ids).exclude(status=CrawlJob.STATE_PENDING).update(
            status=CrawlJob.STATE_PENDING,
            locked_by=None,
            locked_at=None,
            last_error=None,
        )

        # Remove processed ids from zset
        pipe = client.pipeline()
        for jid in job_ids:
            pipe.zrem(SCHEDULE_ZSET, jid)
        pipe.execute()

        logger.info(f"Processed due resets: {updated} jobs → PENDING")
        return int(updated)
    except Exception as e:
        logger.error(f"Error processing due resets: {e}")
        return 0
