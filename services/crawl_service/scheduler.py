"""
Scheduler service for creating tasks from jobs.

Usage:
    from crawl_service.scheduler import CrawlScheduler
    scheduler = CrawlScheduler()
    scheduler.create_tasks()
    scheduler.handle_timeouts()
"""

from django.utils import timezone
from datetime import timedelta
import logging

from .models import CrawlJob, CrawlTask, ScheduleRule

logger = logging.getLogger(__name__)


class CrawlScheduler:
    """Simple scheduler for crawl jobs"""
    
    def create_tasks(self):
        """Create tasks from pending jobs"""
        pending_jobs = CrawlJob.objects.filter(
            status='pending'
        ).select_related('schedule_rule').order_by('-priority')
        
        created = 0
        for job in pending_jobs:
            try:
                # Check schedule
                if job.next_run_at and timezone.now() < job.next_run_at:
                    continue
                
                # Create task
                task = CrawlTask.objects.create(job=job)
                job.status = 'running'
                job.save(update_fields=['status'])
                
                created += 1
                logger.info(f"Created task {task.id} for job {job.url[:50]}")
            
            except Exception as e:
                logger.error(f"Error creating task for {job.url}: {e}")
        
        logger.info(f"Created {created} tasks")
        return created
    
    def handle_timeouts(self):
        """Handle timed-out tasks"""
        now = timezone.now()
        timeout_tasks = CrawlTask.objects.filter(
            status='assigned',
            timeout_at__lt=now
        )
        
        handled = 0
        for task in timeout_tasks:
            try:
                task.status = 'failed'
                task.save(update_fields=['status'])
                
                task.job.status = 'timeout'
                task.job.retry_count += 1
                task.job.save(update_fields=['status', 'retry_count'])
                
                handled += 1
                logger.warning(f"Task {task.id} timeout")
            
            except Exception as e:
                logger.error(f"Error handling timeout: {e}")
        
        logger.info(f"Handled {handled} timeout tasks")
        return handled
    
    def retry_failed_jobs(self):
        """Retry failed jobs that have retries left"""
        failed_jobs = CrawlJob.objects.filter(
            status='failed',
            retry_count__lt=models.F('max_retries')
        )
        
        retried = 0
        for job in failed_jobs:
            try:
                job.status = 'pending'
                job.last_error = None
                job.save(update_fields=['status', 'last_error'])
                retried += 1
            
            except Exception as e:
                logger.error(f"Error retrying job {job.id}: {e}")
        
        logger.info(f"Retried {retried} failed jobs")
        return retried
