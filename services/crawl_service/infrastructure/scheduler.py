"""
Crawl Scheduler - Infrastructure Service

This service orchestrates the scheduling of crawl jobs.
It should be called by Celery Beat, cron job, or Django management command.
"""

from typing import List
from datetime import datetime
import logging
import uuid

from ..repositories.interfaces import ICrawlJobRepository, ICrawlTaskRepository
from ..domain.entities import CrawlJob, CrawlTask, JobStatus, TaskStatus
from ..domain.services import JobSchedulingService

logger = logging.getLogger(__name__)


class CrawlScheduler:
    """
    Infrastructure service for scheduled job execution.
    
    Responsibilities:
    - Find jobs that are due for execution
    - Create tasks for those jobs
    - Handle task timeouts
    """
    
    def __init__(
        self,
        job_repo: ICrawlJobRepository,
        task_repo: ICrawlTaskRepository
    ):
        self.job_repo = job_repo
        self.task_repo = task_repo
        self.scheduling_service = JobSchedulingService()
    
    def execute_due_jobs(self) -> int:
        """
        Main scheduler entry point.
        Find jobs due for execution and create tasks.
        
        Returns:
            Number of tasks created
        """
        current_time = datetime.utcnow()
        due_jobs = self.job_repo.get_jobs_due_for_execution(current_time)
        
        tasks_created = 0
        
        for job in due_jobs:
            try:
                if self.scheduling_service.should_execute_now(job, current_time):
                    task = self._create_task_for_job(job)
                    job.mark_running()
                    self.job_repo.update(job)
                    tasks_created += 1
                    logger.info(
                        f"Created task {task.id} for job {job.id} "
                        f"(tenant: {job.tenant_id})"
                    )
            
            except Exception as e:
                logger.error(f"Failed to create task for job {job.id}: {e}", exc_info=True)
                job.mark_failed(str(e))
                self.job_repo.update(job)
        
        if tasks_created > 0:
            logger.info(f"Scheduler created {tasks_created} tasks")
        
        return tasks_created
    
    def handle_timeout_tasks(self) -> int:
        """
        Find tasks that exceeded timeout and mark them failed.
        Also update corresponding jobs.
        
        Returns:
            Number of tasks handled
        """
        current_time = datetime.utcnow()
        timeout_tasks = self.task_repo.get_timeout_tasks(current_time)
        
        handled = 0
        for task in timeout_tasks:
            try:
                task.mark_failed()
                self.task_repo.update(task)
                
                # Get job (cross-tenant, so pass None for tenant_id in a general get)
                # Note: We need to get job without tenant filter
                # This is a simplification - in production, store tenant_id in task or use different method
                job = self._get_job_for_task(task)
                if job:
                    job.mark_timeout()
                    self.job_repo.update(job)
                    logger.warning(
                        f"Task {task.id} timed out for job {job.id} "
                        f"(bot: {task.bot_id})"
                    )
                
                handled += 1
            
            except Exception as e:
                logger.error(f"Failed to handle timeout for task {task.id}: {e}", exc_info=True)
        
        if handled > 0:
            logger.warning(f"Handled {handled} timeout tasks")
        
        return handled
    
    def retry_failed_jobs(self) -> int:
        """
        Find failed jobs that can be retried and reset them to pending.
        
        Returns:
            Number of jobs reset for retry
        """
        # This would need a method to get failed jobs
        # Simplified implementation - to be enhanced based on requirements
        retry_count = 0
        logger.info("Retry logic not yet implemented")
        return retry_count
    
    def _create_task_for_job(self, job: CrawlJob) -> CrawlTask:
        """Create a new task for a job"""
        task = CrawlTask(
            id=uuid.uuid4(),
            job_id=job.id,
            status=TaskStatus.QUEUED
        )
        return self.task_repo.create(task)
    
    def _get_job_for_task(self, task: CrawlTask) -> CrawlJob:
        """
        Get job for a task.
        Simplified - in production, might need to store tenant_id in task
        or use a join query.
        """
        # This is a workaround - ideally task should have tenant_id
        # or we query directly from Django models with join
        from ..infrastructure.django_models import CrawlJobModel
        try:
            job_model = CrawlJobModel.objects.get(id=task.job_id)
            from ..repositories.implementations import DjangoCrawlJobRepository
            return DjangoCrawlJobRepository._to_entity(job_model)
        except CrawlJobModel.DoesNotExist:
            return None
