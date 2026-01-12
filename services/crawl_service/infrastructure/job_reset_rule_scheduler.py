"""
JobResetRule Scheduler Manager

Executes JobResetRule frequency-based resets asynchronously.
Runs in a background daemon thread with singleton pattern.
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


class JobResetRuleScheduler:
    """
    Thread-safe singleton scheduler for JobResetRule frequency-based execution.
    
    Pattern:
    - get_scheduler() returns singleton instance
    - start() starts daemon thread
    - stop() stops daemon thread
    - run_resets() executes pending rules
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        self.running = False
        self.thread = None
        self._config = {
            'interval': 60,  # Check every 60 seconds
            'check_interval': 10,  # Check rule execution every N cycles
        }
        self.stats = {
            'started_at': None,
            'last_run_at': None,
            'total_cycles': 0,
            'total_rules_executed': 0,
            'total_jobs_reset': 0,
            'last_error': None,
        }
        # Track last execution time per rule
        self.rule_last_execution = {}
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance with thread safety"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def is_running(self) -> bool:
        """Check if scheduler thread is running"""
        return self.running and self.thread and self.thread.is_alive()
    
    def start(self) -> tuple:
        """
        Start scheduler in background daemon thread.
        
        Returns: (success: bool, message: str)
        """
        with self._lock:
            if self.is_running():
                return True, "JobResetRule scheduler already running"
            
            try:
                self.running = True
                self.stats['started_at'] = timezone.now().isoformat()
                
                self.thread = threading.Thread(
                    target=self._run_scheduler_loop,
                    daemon=True,
                    name="JobResetRuleScheduler"
                )
                self.thread.start()
                
                logger.info("✓ JobResetRule scheduler started")
                return True, "JobResetRule scheduler started successfully"
                
            except Exception as e:
                self.running = False
                error_msg = f"Failed to start scheduler: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return False, error_msg
    
    def stop(self) -> tuple:
        """
        Stop scheduler thread gracefully.
        
        Returns: (success: bool, message: str)
        """
        with self._lock:
            if not self.is_running():
                return True, "JobResetRule scheduler not running"
            
            try:
                self.running = False
                
                # Wait for thread to finish (max 5 seconds)
                if self.thread:
                    self.thread.join(timeout=5)
                    if self.thread.is_alive():
                        logger.warning("JobResetRule scheduler thread did not stop gracefully")
                
                logger.info("✓ JobResetRule scheduler stopped")
                return True, "JobResetRule scheduler stopped successfully"
                
            except Exception as e:
                error_msg = f"Error stopping scheduler: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return False, error_msg
    
    def _run_scheduler_loop(self):
        """Main scheduler loop (runs in background thread)"""
        cycle = 0
        
        logger.info(f"JobResetRule scheduler loop started (interval={self._config['interval']}s)")
        
        while self.running:
            try:
                cycle += 1
                self.stats['total_cycles'] = cycle
                self.stats['last_run_at'] = timezone.now().isoformat()
                
                # Check for rule execution every N cycles
                if cycle % self._config['check_interval'] == 0:
                    self.run_resets()
                
                time.sleep(self._config['interval'])
            
            except Exception as e:
                error_msg = f"Error in JobResetRule scheduler cycle {cycle}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.stats['last_error'] = error_msg
                
                # Sleep before retry
                time.sleep(self._config['interval'])
        
        logger.info(f"JobResetRule scheduler loop stopped after {cycle} cycles")
    
    def run_resets(self):
        """
        Execute pending JobResetRule resets.
        
        For each enabled rule, check if frequency has elapsed since last execution.
        If yes, find matching jobs and reset them to PENDING.
        """
        from ..models import JobResetRule, CrawlJob
        from .redis_job_scheduler import schedule_reset_to_pending
        
        try:
            rules = JobResetRule.enabled_rules()
            rules_executed = 0
            total_jobs_reset = 0
            
            for rule in rules:
                rule_id = str(rule.id)
                last_exec = self.rule_last_execution.get(rule_id)
                
                # Check if frequency has elapsed
                if last_exec:
                    elapsed = timezone.now() - last_exec
                    if elapsed.total_seconds() < rule.frequency_hours * 3600:
                        continue  # Not yet time to execute
                
                # Build query of matching DONE jobs
                qs = CrawlJob.objects.filter(status='done')
                
                if rule.selection_type == rule.SelectionType.DOMAIN and rule.domain:
                    qs = qs.filter(product_url__domain=rule.domain)
                elif rule.selection_type == rule.SelectionType.DOMAIN_REGEX and rule.domain_regex:
                    qs = qs.filter(product_url__domain__name__regex=rule.domain_regex)
                elif rule.selection_type == rule.SelectionType.URL_REGEX and rule.url_pattern:
                    qs = qs.filter(product_url__normalized_url__regex=rule.url_pattern)
                elif rule.selection_type == rule.SelectionType.RULE and rule.rule_tag:
                    qs = qs.filter(rule_tag=rule.rule_tag)
                # ALL → no additional filter
                
                job_ids = list(qs.values_list('id', flat=True)[:2000])  # Cap at 2000
                
                if job_ids:
                    # Schedule resets to PENDING
                    scheduled = schedule_reset_to_pending(
                        [str(jid) for jid in job_ids],
                        run_at_ts=timezone.now().timestamp()
                    )
                    
                    if scheduled > 0:
                        self.rule_last_execution[rule_id] = timezone.now()
                        rules_executed += 1
                        total_jobs_reset += scheduled
                        
                        logger.info(
                            f"[JobResetRule] '{rule.name}' executed: "
                            f"scheduled {scheduled} job(s) to PENDING "
                            f"(frequency: {rule.frequency_hours}h)"
                        )
            
            if rules_executed > 0:
                self.stats['total_rules_executed'] += rules_executed
                self.stats['total_jobs_reset'] += total_jobs_reset
                
        except Exception as e:
            error_msg = f"Error running JobResetRule resets: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.stats['last_error'] = error_msg


# Singleton instance
_scheduler = JobResetRuleScheduler.get_instance()


def get_job_reset_rule_scheduler() -> JobResetRuleScheduler:
    """Get singleton JobResetRule scheduler instance"""
    return _scheduler
