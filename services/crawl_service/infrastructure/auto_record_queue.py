"""
Redis-backed Auto-Record Queue

Purpose:
- Queue CrawlResult IDs for async auto-record to PriceHistory
- Process queue asynchronously via scheduler
- Support retries for failed recordings
- Avoid direct database writes on CrawlResult post_save signal

Pattern:
1. Signal handler enqueues result_id to Redis
2. Scheduler processes queue periodically
3. For each result: check criteria → write to PriceHistory
4. Mark as recorded or retry on failure
"""

import logging
import time
from typing import List, Optional
from decimal import Decimal

from django.utils import timezone

from .redis_adapter import get_cache_service
from ..models import CrawlResult

logger = logging.getLogger(__name__)

# Redis keys
AUTO_RECORD_QUEUE = "crawl:auto_record:queue"  # List of result IDs to process
AUTO_RECORD_PROCESSING = "crawl:auto_record:processing"  # Set of IDs being processed
AUTO_RECORD_FAILED = "crawl:auto_record:failed"  # Set of IDs that failed


def enqueue_auto_record(result_id: str) -> bool:
    """Enqueue a CrawlResult ID for async auto-recording.
    
    Called from post_save signal to avoid blocking.
    
    Args:
        result_id: UUID of CrawlResult to record
        
    Returns:
        True if enqueued successfully, False if error
    """
    try:
        cache = get_cache_service()
        client = getattr(cache, "_client", None)
        if not client:
            logger.warning(f"Redis not available; cannot enqueue result {result_id}")
            return False
        
        # Add to queue
        client.rpush(AUTO_RECORD_QUEUE, str(result_id))
        logger.debug(f"Enqueued result {result_id} for auto-record")
        return True
    except Exception as e:
        logger.error(f"Failed to enqueue result {result_id}: {e}")
        return False


def process_auto_record_queue(batch_size: int = 50, max_retries: int = 3) -> dict:
    """Process auto-record queue with status tracking.
    
    Called periodically by scheduler (e.g., every 5 seconds).
    
    Updates CrawlResult.auto_record_eligibility_status:
    - 'processing' when dequeued
    - 'completed' on success
    - 'failed' on permanent failure
    - 'queued' when re-enqueued for retry
    
    Args:
        batch_size: Max results to process per call
        max_retries: Max retry attempts for failed results
        
    Returns:
        Dict with stats: {processed, recorded, failed, duplicates}
    """
    try:
        cache = get_cache_service()
        client = getattr(cache, "_client", None)
        if not client:
            logger.warning("Redis not available; skipping auto-record queue processing")
            return {"processed": 0, "recorded": 0, "failed": 0, "duplicates": 0}
        
        stats = {"processed": 0, "recorded": 0, "failed": 0, "duplicates": 0}
        
        for _ in range(batch_size):
            # Pop from queue (FIFO)
            result_id = client.lpop(AUTO_RECORD_QUEUE)
            if not result_id:
                break  # Queue empty
            
            result_id = result_id.decode('utf-8') if isinstance(result_id, bytes) else result_id
            
            # Check if already being processed (prevent duplicate processing)
            if client.sismember(AUTO_RECORD_PROCESSING, result_id):
                logger.debug(f"Result {result_id} already being processed, skipping")
                continue
            
            # Mark as processing (both Redis and DB)
            client.sadd(AUTO_RECORD_PROCESSING, result_id)
            CrawlResult.objects.filter(id=result_id).update(
                auto_record_eligibility_status='processing'
            )
            
            try:
                # Try to get result from DB
                result = CrawlResult.objects.filter(id=result_id).first()
                if not result:
                    logger.warning(f"CrawlResult {result_id} not found, removing from processing")
                    client.srem(AUTO_RECORD_PROCESSING, result_id)
                    stats["processed"] += 1
                    continue
                
                # Check if already recorded
                if result.history_recorded:
                    logger.debug(f"Result {result_id} already recorded, skipping")
                    client.srem(AUTO_RECORD_PROCESSING, result_id)
                    CrawlResult.objects.filter(id=result_id).update(
                        auto_record_eligibility_status='completed',
                        auto_record_ineligible_reason='Already recorded'
                    )
                    stats["processed"] += 1
                    continue
                
                # Try to auto-record
                from .auto_recording import should_auto_record, write_price_history_for_result
                
                is_eligible, reason = should_auto_record(result)
                if not is_eligible:
                    logger.debug(f"Result {result_id} does not meet auto-record criteria: {reason}")
                    client.srem(AUTO_RECORD_PROCESSING, result_id)
                    CrawlResult.objects.filter(id=result_id).update(
                        auto_record_eligibility_status='ineligible',
                        auto_record_ineligible_reason=reason
                    )
                    stats["processed"] += 1
                    continue
                
                # Write to price history
                success = write_price_history_for_result(result)
                
                if success:
                    logger.info(f"✓ Auto-recorded result {result_id} to PriceHistory")
                    CrawlResult.objects.filter(id=result_id).update(
                        auto_record_eligibility_status='completed'
                    )
                    stats["recorded"] += 1
                elif result.history_record_status == 'duplicate':
                    logger.debug(f"Result {result_id} is duplicate (same price as latest)")
                    CrawlResult.objects.filter(id=result_id).update(
                        auto_record_eligibility_status='completed',
                        auto_record_ineligible_reason='Duplicate price (same as latest)'
                    )
                    stats["duplicates"] += 1
                else:
                    logger.warning(f"Result {result_id} recording failed, marking for retry")
                    # Track failed for retry
                    failure_count = int(client.get(f"crawl:auto_record:failures:{result_id}") or 0) + 1
                    
                    if failure_count < max_retries:
                        # Retry: re-enqueue at end of queue
                        client.rpush(AUTO_RECORD_QUEUE, result_id)
                        client.set(f"crawl:auto_record:failures:{result_id}", failure_count, ex=3600)
                        CrawlResult.objects.filter(id=result_id).update(
                            auto_record_eligibility_status='queued',
                            auto_record_ineligible_reason=f'Retry {failure_count}/{max_retries}'
                        )
                        logger.debug(f"Re-enqueued result {result_id} for retry (attempt {failure_count})")
                        stats["failed"] += 1
                    else:
                        # Max retries exceeded
                        logger.error(f"Result {result_id} failed after {max_retries} retries, giving up")
                        client.sadd(AUTO_RECORD_FAILED, result_id)
                        client.delete(f"crawl:auto_record:failures:{result_id}")
                        CrawlResult.objects.filter(id=result_id).update(
                            auto_record_eligibility_status='failed',
                            auto_record_ineligible_reason=f'Failed after {max_retries} retries'
                        )
                        stats["failed"] += 1
                
                # Mark as processed
                client.srem(AUTO_RECORD_PROCESSING, result_id)
                stats["processed"] += 1
                
            except Exception as e:
                logger.error(f"Error processing result {result_id}: {e}", exc_info=True)
                client.srem(AUTO_RECORD_PROCESSING, result_id)
                CrawlResult.objects.filter(id=result_id).update(
                    auto_record_eligibility_status='failed',
                    auto_record_ineligible_reason=f'Processing error: {str(e)[:150]}'
                )
                stats["processed"] += 1
        
        return stats
        
    except Exception as e:
        logger.error(f"Error in auto-record queue processing: {e}", exc_info=True)
        return {"processed": 0, "recorded": 0, "failed": 0, "duplicates": 0}


def get_auto_record_queue_status() -> dict:
    """Get current queue status.
    
    Returns:
        Dict: {queue_size, processing_size, failed_size}
    """
    try:
        cache = get_cache_service()
        client = getattr(cache, "_client", None)
        if not client:
            return {"queue_size": 0, "processing_size": 0, "failed_size": 0}
        
        return {
            "queue_size": client.llen(AUTO_RECORD_QUEUE),
            "processing_size": client.scard(AUTO_RECORD_PROCESSING),
            "failed_size": client.scard(AUTO_RECORD_FAILED),
        }
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return {"queue_size": 0, "processing_size": 0, "failed_size": 0}


def retry_failed_recordings(limit: int = 10) -> int:
    """Retry failed recordings from failed set.
    
    Called periodically to retry permanently failed results.
    
    Args:
        limit: Max results to retry
        
    Returns:
        Number of results re-enqueued
    """
    try:
        cache = get_cache_service()
        client = getattr(cache, "_client", None)
        if not client:
            return 0
        
        count = 0
        for _ in range(limit):
            result_id = client.spop(AUTO_RECORD_FAILED)
            if not result_id:
                break
            
            result_id = result_id.decode('utf-8') if isinstance(result_id, bytes) else result_id
            client.rpush(AUTO_RECORD_QUEUE, result_id)
            client.delete(f"crawl:auto_record:failures:{result_id}")
            count += 1
        
        if count > 0:
            logger.info(f"Re-enqueued {count} failed results for retry")
        
        return count
    except Exception as e:
        logger.error(f"Error retrying failed recordings: {e}")
        return 0


def clear_auto_record_queue() -> dict:
    """Clear all auto-record queues (for maintenance/reset).
    
    Returns:
        Dict: {cleared_queue, cleared_processing, cleared_failed}
    """
    try:
        cache = get_cache_service()
        client = getattr(cache, "_client", None)
        if not client:
            return {"cleared_queue": 0, "cleared_processing": 0, "cleared_failed": 0}
        
        result = {
            "cleared_queue": client.delete(AUTO_RECORD_QUEUE),
            "cleared_processing": client.delete(AUTO_RECORD_PROCESSING),
            "cleared_failed": client.delete(AUTO_RECORD_FAILED),
        }
        logger.info(f"Cleared auto-record queues: {result}")
        return result
    except Exception as e:
        logger.error(f"Error clearing queues: {e}")
        return {"cleared_queue": 0, "cleared_processing": 0, "cleared_failed": 0}
