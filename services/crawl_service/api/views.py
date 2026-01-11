"""
API Layer - Bot Endpoints with State Machine

Pull-based bot architecture:
1. POST /api/crawl/pull/ - Bot pulls available PENDING jobs, acquires lock
2. POST /api/crawl/submit/ - Bot submits result, transitions to DONE/FAILED, reschedules policy

State transitions:
  Pull: PENDING → LOCKED (bot acquires lock)
  Submit: LOCKED → DONE or LOCKED → FAILED (with auto-retry if retries remain)

Authentication:
  All endpoints require:
  - bot_id: bot identifier from BotConfig
  - api_token: API token from BotConfig

Caching:
  - Pending jobs list cached to reduce DB load for /pull/
  - Job details cached for faster /submit/ lookups
  - Cache invalidation on state changes
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
import logging

from ..models import CrawlJob, CrawlResult
from .serializers import (
    BotPullRequestSerializer,
    JobResponseSerializer,
    CrawlResultSubmissionSerializer,
    ResultResponseSerializer,
)
from .auth import authenticate_bot, auth_error_response
from ..infrastructure.redis_adapter import get_cache_service
from ..domain.cache_service import CacheKeyBuilder

logger = logging.getLogger(__name__)


class BotPullJobsView(APIView):
    """
    Bot pulls available PENDING jobs and acquires lock.
    
    POST /api/crawl/pull/
    Request:
    {
        "bot_id": "bot-001",
        "max_jobs": 10,
        "domain": "example.com"  # optional, filter by domain
    }
    
    Response:
    {
        "success": true,
        "data": {
            "jobs": [
                {
                    "job_id": "uuid",
                    "url": "https://...",
                    "priority": 10,
                    "max_retries": 3,
                    "timeout_seconds": 600,
                    "retry_count": 0,
                    "locked_until": "2025-01-XX..."
                }
            ],
            "count": 1
        }
    }
    
    On error (already locked by another bot):
    {
        "success": false,
        "error": "job_already_locked",
        "detail": "Job is currently locked by bot-002"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            # Opportunistically process due job resets from Redis before serving jobs
            try:
                from ..infrastructure.redis_job_scheduler import process_due_resets
                process_due_resets(max_batch=500)
            except Exception as e:
                logger.warning(f"Reset processing skipped: {e}")
            # Validate request
            serializer = BotPullRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'validation_error',
                    'detail': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            bot_id = serializer.validated_data['bot_id']
            api_token = serializer.validated_data['api_token']
            
            # Authenticate bot
            is_authenticated, result = authenticate_bot(bot_id, api_token)
            if not is_authenticated:
                return auth_error_response(result)
            
            bot_config = result
            
            max_jobs = min(
                serializer.validated_data.get('max_jobs', 10),
                bot_config.max_jobs_per_pull
            )
            domain = (serializer.validated_data.get('domain') or '').strip() or None
            
            # Update bot stats
            bot_config.increment_pull()
            
            # === CACHE LAYER: Try to get pending jobs from cache ===
            cache = get_cache_service()
            cache_key = CacheKeyBuilder.pending_jobs(domain=domain)
            cached_jobs = None
            
            try:
                cached_jobs = cache.get(cache_key)
                if cached_jobs:
                    logger.debug(f"Cache HIT for pending jobs: {cache_key}")
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
            
            # If cache miss or disabled, query database
            if cached_jobs is None:
                logger.debug(f"Cache MISS for pending jobs: {cache_key}")
                
                # Query PENDING jobs (not yet locked)
                jobs_qs = CrawlJob.objects.select_related('product_url', 'product_url__domain').filter(
                    status=CrawlJob.STATE_PENDING
                )
                
                # Filter by domain if provided
                if domain:
                    jobs_qs = jobs_qs.filter(product_url__domain__name__icontains=domain)
                
                # Order by priority DESC, created_at ASC
                jobs_qs = jobs_qs.order_by('-priority', 'created_at')[:max_jobs * 3]  # Fetch more for cache
                
                # Build job list for cache
                jobs_list = list(jobs_qs)
                
                # Cache the result (with short TTL for pending jobs)
                try:
                    cache.set(cache_key, [
                        {
                            'id': str(job.id),
                            'url': job.product_url.normalized_url,
                            'priority': job.priority,
                            'max_retries': job.max_retries,
                            'timeout': job.lock_ttl_seconds,
                            'retry_count': job.retry_count,
                        }
                        for job in jobs_list
                    ], ttl_seconds=60)  # Short TTL for pending jobs list
                except Exception as e:
                    logger.warning(f"Cache write error: {e}")
            else:
                # Use cached data, convert back to job IDs for querying
                jobs_list = CrawlJob.objects.filter(
                    id__in=[job['id'] for job in cached_jobs[:max_jobs]],
                    status=CrawlJob.STATE_PENDING
                ).select_related('product_url', 'product_url__domain')
            
            # Attempt to lock jobs for this bot
            assigned_jobs = []
            failed_locks = []
            
            for job in jobs_list[:max_jobs]:  # Limit to requested max_jobs
                # Attempt to lock the job
                if job.lock_for_bot(bot_id):
                    # Lock successful - invalidate cache
                    try:
                        cache.delete(CacheKeyBuilder.job_detail(str(job.id)))
                        cache.delete(cache_key)  # Invalidate pending list
                    except Exception as e:
                        logger.warning(f"Cache invalidation error: {e}")
                    
                    timeout_at = timezone.now() + timezone.timedelta(
                        seconds=job.lock_ttl_seconds
                    )
                    assigned_jobs.append({
                        'job_id': str(job.id),
                        'url': job.product_url.normalized_url,
                        'priority': job.priority,
                        'max_retries': job.max_retries,
                        'timeout_seconds': job.lock_ttl_seconds,
                        'retry_count': job.retry_count,
                        'locked_until': timeout_at.isoformat(),
                    })
                else:
                    # Lock failed - job already locked by another bot
                    failed_locks.append({
                        'job_id': str(job.id),
                        'url': job.product_url.normalized_url,
                        'locked_by': job.locked_by,
                    })
            
            logger.info(
                f"Bot {bot_id} pulled {len(assigned_jobs)} jobs "
                f"({len(failed_locks)} already locked)"
            )
            
            return Response({
                'success': True,
                'data': {
                    'jobs': assigned_jobs,
                    'count': len(assigned_jobs),
                    'skipped': len(failed_locks),  # Jobs already locked by other bots
                }
            })
        
        except Exception as e:
            logger.error(f"Error in pull endpoint: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': 'internal_error',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BotSubmitResultView(APIView):
    """
    Bot submits crawl result after executing job.
    
    POST /api/crawl/submit/
    Request:
    {
        "bot_id": "bot-001",
        "job_id": "uuid",
        "success": true,
        "price": 99.99,
        "currency": "USD",
        "title": "Product Name",
        "in_stock": true,
        "parsed_data": {...},
        "raw_html": "...",
        "error_msg": ""  # if success=false
    }
    
    Response (success=true):
    {
        "success": true,
        "data": {
            "result_id": "uuid",
            "job_id": "uuid",
            "status": "done",
            "price": 99.99,
            "currency": "USD",
            "policy_next_run": "2025-01-XX..."
        }
    }
    
    Response (success=false, with auto-retry):
    {
        "success": true,
        "data": {
            "job_id": "uuid",
            "status": "pending",  # auto-transitioned back to pending
            "retry_count": 1,
            "max_retries": 3,
            "message": "Job marked for retry"
        }
    }
    
    Errors:
    - job_not_found: Job ID doesn't exist
    - job_not_locked: Job is not in LOCKED state
    - not_assigned: Job not locked by this bot
    - lock_expired: Lock TTL exceeded
    - retries_exhausted: No more retries available
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            # Validate request
            serializer = CrawlResultSubmissionSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'validation_error',
                    'detail': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            data = serializer.validated_data
            bot_id = data['bot_id']
            api_token = data['api_token']
            job_id = data['job_id']
            success = data['success']
            
            # Authenticate bot
            is_authenticated, result = authenticate_bot(bot_id, api_token)
            if not is_authenticated:
                return auth_error_response(result)
            
            bot_config = result
            
            # === CACHE LAYER: Try to get job from cache ===
            cache = get_cache_service()
            job_cache_key = CacheKeyBuilder.job_detail(str(job_id))
            
            # Get job (from cache or DB)
            try:
                job = CrawlJob.objects.select_related('product_url').get(id=job_id)
                
                # Cache job details for future lookups
                try:
                    cache.set(job_cache_key, {
                        'id': str(job.id),
                        'status': job.status,
                        'locked_by': job.locked_by,
                        'locked_at': job.locked_at.isoformat() if job.locked_at else None,
                    }, ttl_seconds=600)
                except Exception as e:
                    logger.warning(f"Cache write error: {e}")
                    
            except CrawlJob.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'job_not_found',
                    'detail': f'Job {job_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Verify job is LOCKED
            if job.status != CrawlJob.STATE_LOCKED:
                return Response({
                    'success': False,
                    'error': 'job_not_locked',
                    'detail': f'Job is in {job.status} state, expected locked'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify lock ownership
            if job.locked_by != bot_id:
                return Response({
                    'success': False,
                    'error': 'not_assigned',
                    'detail': f'Job locked by {job.locked_by}, not {bot_id}'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check if lock expired
            if job.is_lock_expired():
                job.mark_expired()
                
                # Invalidate cache
                try:
                    cache.delete(job_cache_key)
                    cache.clear_pattern(CacheKeyBuilder.all_jobs_pattern())
                except Exception as e:
                    logger.warning(f"Cache invalidation error: {e}")
                
                return Response({
                    'success': False,
                    'error': 'lock_expired',
                    'detail': 'Lock TTL exceeded'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # ===== Handle Success Case =====
            if success:
                # Create or update result (overwrites previous attempts for the job)
                result, _ = CrawlResult.objects.update_or_create(
                    job=job,
                    defaults={
                        'price': data['price'],
                        'currency': data['currency'],
                        'title': data.get('title') or '',
                        'in_stock': data.get('in_stock', True),
                        'raw_html': data.get('raw_html'),
                        'parsed_data': data.get('parsed_data', {}),
                        'crawled_at': timezone.now(),
                    }
                )
                
                # Transition job: LOCKED → DONE
                job.mark_done()
                
                # === CACHE INVALIDATION on state change ===
                try:
                    cache.delete(job_cache_key)
                    cache.clear_pattern(CacheKeyBuilder.all_jobs_pattern())  # Clear pending lists
                except Exception as e:
                    logger.warning(f"Cache invalidation error: {e}")
                
                # Update bot stats
                bot_config.increment_completed()
                
                # Schedule next reset to PENDING via Redis using matching JobResetRule
                try:
                    from ..models import JobResetRule
                    from ..infrastructure.redis_job_scheduler import schedule_reset_to_pending
                    rule = JobResetRule.match_for_job(job)
                    hours = rule.frequency_hours if rule else 24
                    run_at = timezone.now() + timezone.timedelta(hours=hours)
                    schedule_reset_to_pending([str(job.id)], run_at_ts=run_at.timestamp())
                except Exception as e:
                    logger.warning(f"Reset schedule failed: {e}")
                
                logger.info(
                    f"Job {job_id} completed: {result.price} {result.currency} by {bot_id}"
                )
                
                # NOTE: PriceHistory writing is now handled by products service via signals/events
                # Crawl service only stores CrawlResult, maintaining clean separation of concerns
                
                return Response({
                    'success': True,
                    'data': {
                        'result_id': str(result.id),
                        'job_id': str(job.id),
                        'status': job.status,
                        'price': float(result.price),
                        'currency': result.currency,
                        'next_reset_at': run_at.isoformat()
                    }
                }, status=status.HTTP_201_CREATED)
            
            # ===== Handle Failure Case =====
            else:
                error_msg = data.get('error_msg', 'Unknown error')
                
                # Persist result even on failure for debugging/traceability
                failure_result, _ = CrawlResult.objects.update_or_create(
                    job=job,
                    defaults={
                        'price': Decimal('0.00'),
                        'currency': data.get('currency') or 'N/A',
                        'title': data.get('title') or error_msg[:500],
                        'in_stock': data.get('in_stock', False),
                        'raw_html': data.get('raw_html'),
                        'parsed_data': {
                            **(data.get('parsed_data') or {}),
                            'error_msg': error_msg,
                            'success': False,
                        },
                        'crawled_at': timezone.now(),
                    }
                )
                
                # Check if retries available
                if job.retry_count < job.max_retries - 1:
                    # Auto-retry: transition back to PENDING
                    job.mark_failed(error_msg=error_msg, auto_retry=True)
                    
                    # === CACHE INVALIDATION on retry ===
                    try:
                        cache.delete(job_cache_key)
                        cache.clear_pattern(CacheKeyBuilder.all_jobs_pattern())
                    except Exception as e:
                        logger.warning(f"Cache invalidation error: {e}")
                    
                    # Update bot stats
                    bot_config.increment_failed()
                    
                    logger.warning(
                        f"Job {job_id} failed, auto-retrying "
                        f"({job.retry_count}/{job.max_retries}): {error_msg}"
                    )
                    
                    return Response({
                        'success': True,
                        'data': {
                            'job_id': str(job.id),
                            'result_id': str(failure_result.id),
                            'status': job.status,
                            'retry_count': job.retry_count,
                            'max_retries': job.max_retries,
                            'message': 'Job marked for retry'
                        }
                    })
                else:
                    # Retries exhausted: transition to FAILED
                    job.mark_failed(error_msg=error_msg, auto_retry=False)
                    
                    # === CACHE INVALIDATION on failure ===
                    try:
                        cache.delete(job_cache_key)
                        cache.clear_pattern(CacheKeyBuilder.all_jobs_pattern())
                    except Exception as e:
                        logger.warning(f"Cache invalidation error: {e}")
                    
                    # Update bot stats
                    bot_config.increment_failed()
                    
                    # No automatic reset scheduling on permanent failure.
                    
                    logger.error(
                        f"Job {job_id} failed permanently by {bot_id} "
                        f"(retries exhausted): {error_msg}"
                    )
                    
                    return Response({
                        'success': True,
                        'data': {
                            'job_id': str(job.id),
                            'result_id': str(failure_result.id),
                            'status': job.status,
                            'retry_count': job.retry_count,
                            'max_retries': job.max_retries,
                            'message': 'Retries exhausted',
                            'error': error_msg
                        }
                    })
        
        except Exception as e:
            logger.error(f"Error in submit endpoint: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': 'internal_error',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

