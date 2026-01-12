import logging
import signal
import sys
from django.core.management.base import BaseCommand
from django.utils import timezone
from services.crawl_service.scheduler import CrawlScheduler


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run the crawl scheduler to create tasks and handle timeouts'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.stdout.write(self.style.WARNING('\n⏹️  Shutting down scheduler...'))
        self.running = False
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run scheduler once and exit (default: continuous loop)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Scheduler interval in seconds (default: 60)',
        )
        parser.add_argument(
            '--timeout-check-interval',
            type=int,
            default=30,
            help='Timeout check interval in seconds (default: 30)',
        )
    
    def handle(self, *args, **options):
        once = options['once']
        interval = options['interval']
        timeout_interval = options['timeout_check_interval']
        
        self.stdout.write(self.style.SUCCESS('✅ Crawl Scheduler Started'))
        self.stdout.write(f'📊 Mode: {"Single Run" if once else "Continuous Loop"}')
        if not once:
            self.stdout.write(f'⏱️  Interval: {interval}s (Create tasks) / {timeout_interval}s (Check timeouts)')
        
        scheduler = CrawlScheduler()
        last_timeout_check = timezone.now()
        
        try:
            if once:
                self._run_once(scheduler)
            else:
                self._run_continuous(scheduler, interval, timeout_interval)
        
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n⚠️  Scheduler interrupted by user'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Scheduler error: {str(e)}'))
            logger.exception('Crawl scheduler error')
            raise
    
    def _run_once(self, scheduler):
        """Run scheduler once"""
        self.stdout.write('🔄 Running auto-record scheduler once...')
        
        try:
            # Process auto-record queue
            stats = scheduler.process_auto_record_queue()
            if stats["processed"] > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'📝 Auto-record: processed={stats["processed"]} recorded={stats["recorded"]} duplicates={stats["duplicates"]} failed={stats["failed"]}')
                )
            else:
                self.stdout.write(self.style.SUCCESS('✅ No items in queue to process'))
            
            # Show queue stats
            from services.crawl_service.infrastructure.auto_record_queue import get_auto_record_queue_status
            queue_status = get_auto_record_queue_status()
            self.stdout.write(f'📊 Queue Status:')
            self.stdout.write(f'  • Queue size: {queue_status["queue_size"]}')
            self.stdout.write(f'  • Processing: {queue_status["processing_count"]}')
            self.stdout.write(f'  • Failed: {queue_status["failed_count"]}')
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            logger.exception('Error in single run')
            raise
    
    def _run_continuous(self, scheduler, interval, timeout_interval):
        """Run scheduler in continuous loop"""
        import time
        
        self.stdout.write(
            self.style.SUCCESS(f'🚀 Auto-record scheduler running continuously (Ctrl+C to stop)...')
        )
        self.stdout.write('')
        
        cycle = 0
        
        while self.running:
            try:
                cycle += 1
                now = timezone.now()
                
                # Process auto-record queue
                self.stdout.write(f'[Cycle {cycle}] Processing auto-record queue...')
                stats = scheduler.process_auto_record_queue()
                
                if stats["processed"] > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f'  📝 Processed: {stats["processed"]} | Recorded: {stats["recorded"]} | Duplicates: {stats["duplicates"]} | Failed: {stats["failed"]}')
                    )
                else:
                    self.stdout.write(self.style.SUCCESS(f'  ✅ Queue empty'))
                
                # Show queue status every 10 cycles
                if cycle % 10 == 0:
                    from services.crawl_service.infrastructure.auto_record_queue import get_auto_record_queue_status
                    queue_status = get_auto_record_queue_status()
                    self.stdout.write(f'  📊 Queue: {queue_status["queue_size"]} | Processing: {queue_status["processing_count"]} | Failed: {queue_status["failed_count"]}')
                
                self.stdout.write('')
                
                # Sleep before next cycle
                time.sleep(interval)
            
            except KeyboardInterrupt:
                raise
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Error in cycle {cycle}: {str(e)}')
                )
                logger.exception(f'Error in scheduler cycle {cycle}')
                # Continue running even on error
                time.sleep(interval)
