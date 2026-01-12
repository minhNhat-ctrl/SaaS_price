"""
Scheduler service for auto-record queue processing.

Usage:
    from crawl_service.scheduler import CrawlScheduler
    scheduler = CrawlScheduler()
    scheduler.process_auto_record_queue()
"""

from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class CrawlScheduler:
    """Simple scheduler for auto-record queue processing"""
    
    def process_auto_record_queue(self):
        """Process async auto-record queue via Redis.
        
        Called periodically by management command or external scheduler.
        """
        try:
            from .infrastructure.auto_record_queue import (
                process_auto_record_queue,
                retry_failed_recordings,
                get_auto_record_queue_status,
            )
            
            # Process main queue
            stats = process_auto_record_queue(batch_size=100, max_retries=3)
            
            # Periodically retry permanently failed (every N calls)
            if stats["processed"] % 500 == 0:
                retried = retry_failed_recordings(limit=20)
                if retried > 0:
                    logger.info(f"Retried {retried} permanently failed recordings")
            
            # Log status
            queue_status = get_auto_record_queue_status()
            if queue_status["queue_size"] > 0 or stats["recorded"] > 0:
                logger.info(f"Auto-record: processed={stats['processed']} recorded={stats['recorded']} duplicates={stats['duplicates']} failed={stats['failed']} queue_remaining={queue_status['queue_size']}")
            
            return stats
        except Exception as e:
            logger.error(f"Error processing auto-record queue: {e}", exc_info=True)
            return {"processed": 0, "recorded": 0, "failed": 0, "duplicates": 0}
