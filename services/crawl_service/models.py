"""
Crawl Service - Bot-Focused Internal Module

Pull-based bot architecture: Bot chủ động pull job, Crawl Module quản lý trạng thái.

Architecture:
- Models: CrawlPolicy (policy-driven, NOT cron), CrawlJob (state machine), CrawlResult
- API: Pull/Push endpoints for bot with state locking
- Admin: Django-adapter integration, monitoring
- Scheduler: Policy-driven (next_run_at), NOT cron-based
"""

from django.db import models
from django.utils import timezone
import uuid
import logging

logger = logging.getLogger(__name__)


class CrawlPolicy(models.Model):
    """
    Crawl Policy - Quản lý nhóm URLs theo domain/pattern.
    
    Không lưu từng URL cụ thể - chỉ quản lý cấu hình theo domain.
    VD: 1 policy cho tất cả URLs của amazon.co.jp
    Scale tốt cho hàng triệu URLs.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Domain-based grouping (thay vì URL cụ thể)
    domain = models.ForeignKey(
        'products_shared.Domain',
        on_delete=models.CASCADE,
        related_name='crawl_policies',
        null=True,  # Nullable during migration
        blank=True,
        help_text="Domain này policy áp dụng cho"
    )
    name = models.CharField(
        max_length=255,
        default='Default Policy',  # Default for migration
        help_text="Tên policy (VD: 'Amazon JP - High Priority')"
    )
    url_pattern = models.CharField(
        max_length=500,
        blank=True,
        help_text="Regex pattern để filter URLs (optional, empty = all URLs of domain)"
    )
    
    # Frequency config
    frequency_hours = models.IntegerField(default=24, help_text="Crawl every N hours (6/24/168/...)")
    priority = models.IntegerField(
        default=5,
        choices=[(1, 'Low'), (5, 'Normal'), (10, 'High'), (20, 'Urgent')],
        db_index=True,
        help_text="Base priority for this URL"
    )
    
    # Retry config
    max_retries = models.IntegerField(default=3, help_text="Max retry attempts")
    retry_backoff_minutes = models.IntegerField(default=5, help_text="Backoff for retries")
    timeout_minutes = models.IntegerField(default=10, help_text="Crawl timeout")
    
    # Crawl config
    crawl_config = models.JSONField(default=dict, blank=True, help_text="Headers, JS required, etc.")
    
    # Enable/disable
    enabled = models.BooleanField(default=True, db_index=True)
    
    # Tracking
    last_success_at = models.DateTimeField(null=True, blank=True, help_text="Last successful crawl")
    last_failed_at = models.DateTimeField(null=True, blank=True, help_text="Last failed crawl")
    next_run_at = models.DateTimeField(db_index=True, help_text="When scheduler should next create a job")
    failure_count = models.IntegerField(default=0, help_text="Consecutive failures")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crawl_policy'
        verbose_name = 'Crawl Policy'
        verbose_name_plural = 'Crawl Policies'
        indexes = [
            models.Index(fields=['domain', 'enabled']),
            models.Index(fields=['enabled', 'next_run_at']),
            models.Index(fields=['-priority', 'next_run_at']),
        ]
        ordering = ['-priority', 'next_run_at']
        unique_together = [['domain', 'name']]
    
    def __str__(self):
        return f"{self.domain.name} - {self.name} (priority={self.priority})"
    
    def matches_url(self, url: str) -> bool:
        """Check if URL matches this policy's pattern."""
        if not self.url_pattern:
            return True  # Empty pattern = match all URLs of domain
        import re
        try:
            return bool(re.search(self.url_pattern, url))
        except re.error:
            return False
    
    def schedule_next_run(self, success=True):
        """Reschedule next_run_at based on success/failure."""
        if success:
            self.failure_count = 0
            self.last_success_at = timezone.now()
            # Reset to normal frequency
            self.next_run_at = timezone.now() + timezone.timedelta(hours=self.frequency_hours)
        else:
            self.failure_count += 1
            self.last_failed_at = timezone.now()
            # Exponential backoff: 5min, 10min, 20min, ...
            backoff_mins = self.retry_backoff_minutes * (2 ** min(self.failure_count - 1, 3))
            self.next_run_at = timezone.now() + timezone.timedelta(minutes=backoff_mins)
        self.save(update_fields=['next_run_at', 'failure_count', 'last_success_at', 'last_failed_at'])


class CrawlJob(models.Model):
    """
    CrawlJob - individual URL execution với state machine.
    
    State: PENDING → LOCKED → DONE/FAILED/EXPIRED
    Locking: locked_by (bot_id) + locked_at + lock_ttl_seconds
    
    Optimized: Sử dụng url_hash để reference ProductURL thay vì lưu full URL.
    Scale tốt cho hàng triệu URLs.
    """
    STATE_PENDING = 'pending'
    STATE_LOCKED = 'locked'
    STATE_DONE = 'done'
    STATE_FAILED = 'failed'
    STATE_EXPIRED = 'expired'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Policy reference (group-based)
    policy = models.ForeignKey(
        CrawlPolicy,
        on_delete=models.CASCADE,
        related_name='jobs',
        null=True,  # Nullable during migration
        blank=True,
        help_text="Policy áp dụng cho job này"
    )
    
    # ProductURL reference via hash (tối ưu cho hàng triệu URLs)
    product_url = models.ForeignKey(
        'products_shared.ProductURL',
        on_delete=models.CASCADE,
        related_name='crawl_jobs',
        to_field='url_hash',
        db_column='url_hash',
        null=True,  # Nullable during migration
        blank=True,
        help_text="ProductURL được crawl (via hash)"
    )
    
    # State Machine States
    STATE_CHOICES = [
        (STATE_PENDING, 'Pending - Awaiting bot assignment'),
        (STATE_LOCKED, 'Locked - Bot is executing'),
        (STATE_DONE, 'Done - Crawl succeeded'),
        (STATE_FAILED, 'Failed - Crawl failed'),
        (STATE_EXPIRED, 'Expired - Lock TTL exceeded'),
    ]
    status = models.CharField(
        max_length=20,
        default=STATE_PENDING,
        db_index=True,
        choices=STATE_CHOICES,
        help_text="Current execution state"
    )
    
    # Configuration (inherited from policy at job creation)
    priority = models.IntegerField(
        default=5,
        choices=[(1, 'Low'), (5, 'Normal'), (10, 'High'), (20, 'Urgent')],
        db_index=True,
        help_text="Execution priority"
    )
    max_retries = models.IntegerField(default=3)
    timeout_minutes = models.IntegerField(default=10)
    
    # Locking for Concurrency Safety
    locked_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text="Bot ID that currently holds the lock"
    )
    locked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When bot acquired the lock"
    )
    lock_ttl_seconds = models.IntegerField(
        default=600,  # 10 minutes
        help_text="Lock time-to-live: job expires if not completed within TTL"
    )
    
    # Retry tracking
    retry_count = models.IntegerField(default=0)
    last_error = models.TextField(blank=True, null=True)
    
    # Execution tracking
    last_result_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crawl_job'
        verbose_name = 'Crawl Job'
        verbose_name_plural = 'Crawl Jobs'
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['status', '-priority', 'created_at']),
            models.Index(fields=['locked_by', 'locked_at']),
            models.Index(fields=['-priority', 'status']),
        ]
        ordering = ['-priority', '-created_at']
    
    def __str__(self):
        state_badge = {
            'pending': '⏳',
            'locked': '🔒',
            'done': '✓',
            'failed': '✗',
            'expired': '⏱️'
        }.get(self.status, '?')
        url = self.product_url.normalized_url if self.product_url else 'N/A'
        return f"{state_badge} {url[:50]}"
    
    # ===== State Transitions =====
    
    def lock_for_bot(self, bot_id: str) -> bool:
        """
        Attempt to acquire lock for bot execution.
        Only succeeds if status is PENDING or EXPIRED.
        
        Returns: True if lock acquired, False if already locked by another bot.
        """
        if self.status == self.STATE_LOCKED and self.locked_by and self.locked_by != bot_id:
            # Check if lock has expired
            if self.locked_at:
                elapsed = (timezone.now() - self.locked_at).total_seconds()
                if elapsed < self.lock_ttl_seconds:
                    return False  # Still locked by another bot
        
        # Acquire lock
        self.status = self.STATE_LOCKED
        self.locked_by = bot_id
        self.locked_at = timezone.now()
        self.save(update_fields=['status', 'locked_by', 'locked_at'])
        return True
    
    def mark_done(self):
        """Transition LOCKED → DONE after successful crawl."""
        if self.status != self.STATE_LOCKED:
            logger.warning(f"Job {self.id} mark_done: invalid state {self.status}")
            return
        
        self.status = self.STATE_DONE
        self.locked_by = None
        self.locked_at = None
        self.retry_count = 0
        self.last_error = None
        self.last_result_at = timezone.now()
        self.save(update_fields=[
            'status',
            'locked_by',
            'locked_at',
            'retry_count',
            'last_error',
            'last_result_at'
        ])
    
    def mark_failed(self, error_msg: str = '', auto_retry=True):
        """
        Transition LOCKED → FAILED.
        If auto_retry and retries remaining: transition to PENDING for retry.
        
        Args:
            error_msg: Error message
            auto_retry: If True, auto-transition to PENDING if retries remain
        """
        if self.status != self.STATE_LOCKED:
            logger.warning(f"Job {self.id} mark_failed: invalid state {self.status}")
            return
        
        self.retry_count += 1
        self.last_error = error_msg
        self.last_result_at = timezone.now()
        self.locked_by = None
        self.locked_at = None
        
        # Auto-retry logic
        if auto_retry and self.retry_count < self.max_retries:
            self.status = self.STATE_PENDING
            logger.info(f"Job {self.id}: auto-retrying (attempt {self.retry_count + 1}/{self.max_retries})")
        else:
            self.status = self.STATE_FAILED
            logger.error(f"Job {self.id}: failed (retries exhausted)")
        
        self.save(update_fields=[
            'status',
            'retry_count',
            'last_error',
            'last_result_at',
            'locked_by',
            'locked_at'
        ])
    
    def mark_expired(self):
        """Transition LOCKED → EXPIRED when lock TTL exceeded."""
        if self.status != self.STATE_LOCKED:
            return
        
        self.status = self.STATE_EXPIRED
        self.locked_by = None
        self.locked_at = None
        self.save(update_fields=['status', 'locked_by', 'locked_at'])
        logger.warning(f"Job {self.id} expired (lock TTL exceeded)")
    
    # ===== Utility Methods =====
    
    def is_lock_expired(self) -> bool:
        """Check if current lock has exceeded TTL."""
        if self.status != self.STATE_LOCKED or not self.locked_at:
            return False
        
        elapsed_seconds = (timezone.now() - self.locked_at).total_seconds()
        return elapsed_seconds > self.lock_ttl_seconds
    
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return self.retry_count < self.max_retries


class CrawlResult(models.Model):
    """
    Crawl Result - Data returned by bot after executing CrawlJob.
    
    Created by bot via POST /api/crawl/submit/ after crawl execution.
    One result per job (replaces previous if job re-tried).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.OneToOneField(
        CrawlJob,
        on_delete=models.CASCADE,
        related_name='result',
        help_text="Associated crawl job"
    )
    
    # Price data (primary purpose of crawling)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Extracted product price"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Currency code (USD, VND, EUR, etc)"
    )
    
    # Product info
    title = models.CharField(
        max_length=500,
        blank=True,
        help_text="Product title/name"
    )
    in_stock = models.BooleanField(
        default=True,
        help_text="Product availability status"
    )
    
    # Parser data
    raw_html = models.TextField(
        blank=True,
        null=True,
        help_text="Raw HTML snippet (optional, for debugging)"
    )
    parsed_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Full parsed data returned by bot (custom format)"
    )
    
    # Timestamps
    crawled_at = models.DateTimeField(
        help_text="When bot actually performed the crawl"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'crawl_result'
        verbose_name = 'Crawl Result'
        verbose_name_plural = 'Crawl Results'
        indexes = [
            models.Index(fields=['job', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.price} {self.currency} - {self.job.url[:50]}"
    
    def get_price_info(self) -> dict:
        """Return price info as dict."""
        return {
            'price': float(self.price),
            'currency': self.currency,
            'in_stock': self.in_stock,
            'title': self.title,
            'crawled_at': self.crawled_at.isoformat() if self.crawled_at else None,
        }


class BotConfig(models.Model):
    """
    Bot Configuration - manage bot authentication and settings.
    
    Allows admin to configure:
    - Which bots are allowed to pull jobs
    - Bot-specific TTL, rate limits, priorities
    - API authentication tokens
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Bot identification
    bot_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique bot identifier (e.g., 'bot-001')"
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable bot name"
    )
    description = models.TextField(
        blank=True,
        help_text="Bot purpose and configuration details"
    )
    
    # Authentication
    api_token = models.CharField(
        max_length=255,
        blank=True,
        help_text="API authentication token (optional, for future use)"
    )
    
    # Configuration
    enabled = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether bot is allowed to pull jobs"
    )
    max_jobs_per_pull = models.IntegerField(
        default=10,
        help_text="Maximum jobs bot can pull in one request"
    )
    custom_lock_ttl_seconds = models.IntegerField(
        null=True,
        blank=True,
        help_text="Custom lock TTL for this bot (overrides default 600s)"
    )
    rate_limit_per_minute = models.IntegerField(
        default=60,
        help_text="Max API calls per minute for this bot"
    )
    
    # Priority & filtering
    priority_boost = models.IntegerField(
        default=0,
        help_text="Priority boost for jobs pulled by this bot (-10 to +10)"
    )
    allowed_domains = models.JSONField(
        default=list,
        blank=True,
        help_text="List of domains this bot can crawl (empty = all domains)"
    )
    
    # Statistics
    total_jobs_pulled = models.IntegerField(default=0)
    total_jobs_completed = models.IntegerField(default=0)
    total_jobs_failed = models.IntegerField(default=0)
    last_pull_at = models.DateTimeField(null=True, blank=True)
    last_submit_at = models.DateTimeField(null=True, blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bot_config'
        verbose_name = 'Bot Configuration'
        verbose_name_plural = 'Bot Configurations'
        ordering = ['-enabled', 'bot_id']
    
    def __str__(self):
        status = '✓' if self.enabled else '✗'
        return f"{status} {self.bot_id} - {self.name}"
    
    def get_lock_ttl(self) -> int:
        """Get bot-specific or default lock TTL."""
        return self.custom_lock_ttl_seconds or 600
    
    def increment_pull(self):
        """Increment pull counter."""
        self.total_jobs_pulled += 1
        self.last_pull_at = timezone.now()
        self.save(update_fields=['total_jobs_pulled', 'last_pull_at'])
    
    def increment_completed(self):
        """Increment completed counter."""
        self.total_jobs_completed += 1
        self.last_submit_at = timezone.now()
        self.save(update_fields=['total_jobs_completed', 'last_submit_at'])
    
    def increment_failed(self):
        """Increment failed counter."""
        self.total_jobs_failed += 1
        self.last_submit_at = timezone.now()
        self.save(update_fields=['total_jobs_failed', 'last_submit_at'])
    
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self.total_jobs_completed + self.total_jobs_failed
        if total == 0:
            return 0.0
        return (self.total_jobs_completed / total) * 100
