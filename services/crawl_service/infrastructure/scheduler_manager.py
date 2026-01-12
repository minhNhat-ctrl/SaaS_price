"""
Auto-Record Scheduler Manager

Manages background scheduler thread for auto-record queue processing.
Allows start/stop/status via admin UI without requiring command line.

Thread-safe singleton pattern for single scheduler instance.
"""

import threading
import time
import logging
from typing import Optional, Dict
from django.utils import timezone

logger = logging.getLogger(__name__)


class SchedulerManager:
    """Singleton manager for auto-record scheduler thread"""
    
    _instance: Optional['SchedulerManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.stats = {
            'started_at': None,
            'last_run_at': None,
            'total_cycles': 0,
            'total_processed': 0,
            'total_recorded': 0,
            'total_failed': 0,
            'total_duplicates': 0,
            'last_error': None,
        }
        self._config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load scheduler config from auto_record_config.json"""
        from .auto_recording import get_auto_record_config
        
        cfg = get_auto_record_config()
        cron_cfg = cfg.get('_cron_config', {})
        
        return {
            'enabled': cron_cfg.get('scheduler_enabled', True),
            'interval': cron_cfg.get('interval_seconds', 30),
            'batch_size': cron_cfg.get('batch_size', 100),
            'max_retries': cron_cfg.get('max_retries', 3),
            'retry_failed_every_n_cycles': cron_cfg.get('retry_failed_every_n_cycles', 50),
            'retry_failed_limit': cron_cfg.get('retry_failed_limit', 20),
            'log_status_every_n_cycles': cron_cfg.get('log_queue_status_every_n_cycles', 10),
        }
    
    def reload_config(self):
        """Reload configuration from file"""
        self._config = self._load_config()
        logger.info(f"Scheduler config reloaded: interval={self._config['interval']}s, batch_size={self._config['batch_size']}")
    
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self.running and self.thread is not None and self.thread.is_alive()
    
    def get_status(self) -> Dict:
        """Get current scheduler status"""
        from .auto_record_queue import get_auto_record_queue_status
        
        queue_status = get_auto_record_queue_status()
        
        return {
            'running': self.is_running(),
            'config': self._config,
            'stats': self.stats.copy(),
            'queue': queue_status,
        }
    
    def start(self):
        """Start scheduler thread
        
        Returns:
            tuple[bool, str]: (success, message)
        """
        if self.is_running():
            return False, "Scheduler is already running"
        
        if not self._config.get('enabled'):
            return False, "Scheduler is disabled in config (_cron_config.scheduler_enabled = false)"
        
        try:
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True, name="AutoRecordScheduler")
            self.thread.start()
            
            self.stats['started_at'] = timezone.now().isoformat()
            self.stats['total_cycles'] = 0
            self.stats['last_error'] = None
            
            logger.info("✓ Auto-record scheduler started")
            return True, "Scheduler started successfully"
        
        except Exception as e:
            self.running = False
            error_msg = f"Failed to start scheduler: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.stats['last_error'] = error_msg
            return False, error_msg
    
    def stop(self):
        """Stop scheduler thread
        
        Returns:
            tuple[bool, str]: (success, message)
        """
        if not self.is_running():
            return False, "Scheduler is not running"
        
        try:
            self.running = False
            
            # Wait for thread to finish (max 5 seconds)
            if self.thread:
                self.thread.join(timeout=5.0)
            
            logger.info("✓ Auto-record scheduler stopped")
            return True, "Scheduler stopped successfully"
        
        except Exception as e:
            error_msg = f"Error stopping scheduler: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.stats['last_error'] = error_msg
            return False, error_msg
    
    def _run_scheduler(self):
        """Main scheduler loop (runs in background thread)"""
        from ..scheduler import CrawlScheduler
        from .auto_record_queue import retry_failed_recordings
        
        scheduler = CrawlScheduler()
        cycle = 0
        
        logger.info(f"Auto-record scheduler loop started (interval={self._config['interval']}s, batch={self._config['batch_size']})")
        
        while self.running:
            try:
                cycle += 1
                self.stats['total_cycles'] = cycle
                self.stats['last_run_at'] = timezone.now().isoformat()
                
                # Process auto-record queue
                stats = scheduler.process_auto_record_queue()
                
                # Update cumulative stats
                self.stats['total_processed'] += stats.get('processed', 0)
                self.stats['total_recorded'] += stats.get('recorded', 0)
                self.stats['total_failed'] += stats.get('failed', 0)
                self.stats['total_duplicates'] += stats.get('duplicates', 0)
                
                # Log if items were processed
                if stats.get('processed', 0) > 0:
                    logger.info(
                        f"[Cycle {cycle}] Processed: {stats['processed']} | "
                        f"Recorded: {stats['recorded']} | "
                        f"Duplicates: {stats['duplicates']} | "
                        f"Failed: {stats['failed']}"
                    )
                
                # Periodically retry failed recordings
                if cycle % self._config['retry_failed_every_n_cycles'] == 0:
                    retried = retry_failed_recordings(limit=self._config['retry_failed_limit'])
                    if retried > 0:
                        logger.info(f"[Cycle {cycle}] Retried {retried} permanently failed recordings")
                
                # Log queue status periodically
                if cycle % self._config['log_status_every_n_cycles'] == 0:
                    from .auto_record_queue import get_auto_record_queue_status
                    queue_status = get_auto_record_queue_status()
                    logger.info(
                        f"[Cycle {cycle}] Queue status - "
                        f"Size: {queue_status['queue_size']} | "
                        f"Processing: {queue_status['processing_size']} | "
                        f"Failed: {queue_status['failed_size']}"
                    )
                
                # Sleep before next cycle
                time.sleep(self._config['interval'])
            
            except Exception as e:
                error_msg = f"Error in scheduler cycle {cycle}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.stats['last_error'] = error_msg
                
                # Sleep before retry to avoid tight loop on persistent errors
                time.sleep(self._config['interval'])
        
        logger.info(f"Auto-record scheduler loop stopped after {cycle} cycles")


# Singleton instance
_manager = SchedulerManager()


def get_scheduler_manager() -> SchedulerManager:
    """Get singleton scheduler manager instance"""
    return _manager
