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
from django.db.models import Q
from django.utils import timezone
import uuid
import logging

logger = logging.getLogger(__name__)


class CrawlPolicy(models.Model):
    """Describe crawl behaviour for a group of jobs selected by flexible criteria."""

    class SelectionType(models.TextChoices):
        ALL = 'all', 'All jobs'
        DOMAIN = 'domain', 'Exact domain'
        DOMAIN_REGEX = 'domain_regex', 'Domain regex'
        URL_REGEX = 'url_regex', 'URL regex'
        RULE = 'rule', 'Rule tag'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Selection metadata
    name = models.CharField(
        max_length=255,
        default='Default Policy',
        help_text="Tên policy (VD: 'Amazon JP - High Priority')"
    )
    selection_type = models.CharField(
        max_length=20,
        choices=SelectionType.choices,
        default=SelectionType.ALL,
        help_text="Chiến lược chọn jobs (all/domain/domain_regex/url_regex/rule)"
    )
    is_default = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Đánh dấu policy nền áp dụng khi không có policy khác khớp"
    )
    rule_tag = models.CharField(
        max_length=100,
        blank=True,
        help_text="Rule tag để match job khi selection_type = rule"
    )
    domain = models.ForeignKey(
        'products_shared.Domain',
        on_delete=models.CASCADE,
        related_name='crawl_policies',
        null=True,
        blank=True,
        help_text="Domain áp dụng khi selection_type = domain"
    )
    domain_regex = models.CharField(
        max_length=255,
        blank=True,
        help_text="Regex cho domain name khi selection_type = domain_regex"
    )
    url_pattern = models.CharField(
        max_length=500,
        blank=True,
        help_text="Regex cho URL khi selection_type = url_regex"
    )

    # Behaviour configuration
    frequency_hours = models.IntegerField(default=24, help_text="Crawl every N hours (6/24/168/...)")
    priority = models.IntegerField(
        default=5,
        choices=[(1, 'Low'), (5, 'Normal'), (10, 'High'), (20, 'Urgent')],
        db_index=True,
        help_text="Base priority for matching jobs"
    )
    max_retries = models.IntegerField(default=3, help_text="Max retry attempts")
    retry_backoff_minutes = models.IntegerField(default=5, help_text="Backoff for retries")
    timeout_minutes = models.IntegerField(default=10, help_text="Crawl timeout")
    crawl_config = models.JSONField(default=dict, blank=True, help_text="Headers, JS required, etc.")
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
        ordering = ['-priority', 'next_run_at']
        indexes = [
            models.Index(fields=['enabled', 'selection_type']),
            models.Index(fields=['enabled', 'next_run_at']),
            models.Index(fields=['-priority', 'next_run_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['is_default'],
                condition=Q(is_default=True),
                name='crawl_policy_single_default'
            )
        ]

    def __str__(self):
        target = {
            self.SelectionType.ALL: 'All jobs',
            self.SelectionType.DOMAIN: self.domain.name if self.domain else 'domain:—',
            self.SelectionType.DOMAIN_REGEX: f"domain~{self.domain_regex or '—'}",
            self.SelectionType.URL_REGEX: f"url~{self.url_pattern or '—'}",
            self.SelectionType.RULE: f"rule:{self.rule_tag or '—'}",
        }.get(self.selection_type, 'unknown')
        base_tag = ' (base)' if self.is_default else ''
        return f"{self.name}{base_tag} [{target}]"

    def save(self, *args, **kwargs):
        if self.is_default:
            CrawlPolicy.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
            self.selection_type = self.SelectionType.ALL
            if not self.rule_tag:
                self.rule_tag = 'base'
        super().save(*args, **kwargs)

    @classmethod
    def get_default_policy(cls):
        """Return the enabled default policy if it exists."""
        return cls.objects.filter(is_default=True, enabled=True).order_by('-priority').first()

    @classmethod
    def resolved_policies(cls):
        """Return enabled policies ordered by priority for matching operations."""
        return list(cls.objects.filter(enabled=True).order_by('-priority', 'created_at'))

    def matches_product(self, product_url) -> bool:
        """Check if a ProductURL matches the selection criteria."""
        domain_name = None
        url = None
        if product_url is not None:
            domain = getattr(product_url, 'domain', None)
            domain_name = getattr(domain, 'name', None)
            url = getattr(product_url, 'normalized_url', None) or getattr(product_url, 'raw_url', None)
        return self._matches(target_url=url, domain_name=domain_name, job_rule_tag=None)

    def matches_job(self, job) -> bool:
        """Check if an existing CrawlJob matches the policy criteria."""
        product_url = getattr(job, 'product_url', None)
        domain = getattr(product_url, 'domain', None) if product_url else None
        domain_name = getattr(domain, 'name', None)
        url = getattr(product_url, 'normalized_url', None) or getattr(product_url, 'raw_url', None)
        job_rule_tag = getattr(job, 'rule_tag', None)
        return self._matches(target_url=url, domain_name=domain_name, job_rule_tag=job_rule_tag)

    def matches_url(self, url, *, domain_name=None, job_rule_tag=None) -> bool:
        """Backwards compatible matcher for string-based checks."""
        return self._matches(target_url=url, domain_name=domain_name, job_rule_tag=job_rule_tag)

    def _matches(self, *, target_url=None, domain_name=None, job_rule_tag=None) -> bool:
        if not self.enabled:
            return False

        if self.selection_type == self.SelectionType.ALL:
            return True

        if self.selection_type == self.SelectionType.DOMAIN:
            if not self.domain or not domain_name:
                return False
            return self.domain.name == domain_name

        if self.selection_type == self.SelectionType.DOMAIN_REGEX:
            if not self.domain_regex or not domain_name:
                return False
            import re
            try:
                return bool(re.search(self.domain_regex, domain_name))
            except re.error:
                logger.warning("Invalid domain_regex on policy %s", self.id)
                return False

        if self.selection_type == self.SelectionType.URL_REGEX:
            if not self.url_pattern or not target_url:
                return False
            import re
            try:
                return bool(re.search(self.url_pattern, target_url))
            except re.error:
                logger.warning("Invalid url_pattern on policy %s", self.id)
                return False

        if self.selection_type == self.SelectionType.RULE:
            if not self.rule_tag or not job_rule_tag:
                return False
            return self.rule_tag == job_rule_tag

        return False

    def schedule_next_run(self, success: bool = True):
        """Reschedule next_run_at based on success/failure."""
        if success:
            self.failure_count = 0
            self.last_success_at = timezone.now()
            self.next_run_at = timezone.now() + timezone.timedelta(hours=self.frequency_hours)
        else:
            self.failure_count += 1
            self.last_failed_at = timezone.now()
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
    rule_tag = models.CharField(
        max_length=100,
        default='base',
        blank=True,
        db_index=True,
        help_text="Logical rule identifier for policy selection"
    )
    
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
            models.Index(fields=['rule_tag', 'status']),
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

    # History write tracking (admin-driven)
    history_recorded = models.BooleanField(
        default=False,
        help_text="Whether this result has been recorded to shared PriceHistory"
    )
    history_record_status = models.CharField(
        max_length=20,
        default='none',
        help_text="Record outcome: none, recorded, duplicate, failed"
    )
    history_recorded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when recording to PriceHistory was acknowledged"
    )
    
    class Meta:
        db_table = 'crawl_result'
        verbose_name = 'Crawl Result'
        verbose_name_plural = 'Crawl Results'
        indexes = [
            models.Index(fields=['job', '-created_at']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['history_recorded', 'history_record_status']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        url = self.job.product_url.normalized_url if self.job and self.job.product_url else 'N/A'
        return f"{self.price} {self.currency} - {url[:50]}"
    
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


class CrawlCacheConfig(models.Model):
    """
    Cache Configuration - Redis settings for crawl service.
    
    Admin-configurable Redis connection and cache behavior.
    Only one config can be active at a time (singleton pattern).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    SERVICE_CHOICES = (
        ("primary", "Primary Cache"),
        ("secondary", "Secondary Cache"),
        ("products", "Products Cache"),
    )

    # Fixed slot for cache service (max 3 instances)
    service_key = models.CharField(
        max_length=50,
        choices=SERVICE_CHOICES,
        default="primary",
        unique=True,
        db_index=True,
        help_text="Fixed cache slot (max 3 predefined services)"
    )

    # Display name
    name = models.CharField(
        max_length=255,
        default="Default Cache Config",
        help_text="Configuration name for identification"
    )
    
    # Redis connection settings
    redis_host = models.CharField(
        max_length=255,
        default="localhost",
        help_text="Redis server hostname or IP"
    )
    redis_port = models.IntegerField(
        default=6379,
        help_text="Redis server port"
    )
    redis_db = models.IntegerField(
        default=0,
        help_text="Redis database number (0-15)"
    )
    redis_password = models.CharField(
        max_length=255,
        blank=True,
        help_text="Redis password (optional)"
    )
    
    # Cache behavior
    enabled = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Enable/disable caching globally"
    )
    default_ttl_seconds = models.IntegerField(
        default=300,
        help_text="Default TTL for cache entries (seconds)"
    )
    
    # Cache strategies
    cache_pending_jobs = models.BooleanField(
        default=True,
        help_text="Cache pending jobs list for /pull/ endpoint"
    )
    cache_job_details = models.BooleanField(
        default=True,
        help_text="Cache individual job details"
    )
    cache_product_urls = models.BooleanField(
        default=True,
        help_text="Cache ProductURL data"
    )
    
    # TTL overrides
    pending_jobs_ttl_seconds = models.IntegerField(
        default=60,
        help_text="TTL for pending jobs list cache"
    )
    job_details_ttl_seconds = models.IntegerField(
        default=600,
        help_text="TTL for job details cache"
    )
    product_urls_ttl_seconds = models.IntegerField(
        default=1800,
        help_text="TTL for product URL cache (30 min)"
    )
    
    # Status tracking
    is_active = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Is this the active configuration? (only one can be active)"
    )
    last_connection_test = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful connection test"
    )
    connection_status = models.CharField(
        max_length=50,
        default="untested",
        choices=[
            ('untested', 'Untested'),
            ('connected', 'Connected'),
            ('failed', 'Connection Failed'),
        ],
        help_text="Current connection status"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crawl_cache_config'
        verbose_name = 'Cache Configuration'
        verbose_name_plural = 'Cache Configurations'
        ordering = ['-is_active', '-created_at']
        constraints = [
            models.UniqueConstraint(fields=['service_key'], name='uniq_cache_service_key'),
        ]
    
    def __str__(self):
        status = '✓' if self.is_active else '✗'
        enabled = '🟢' if self.enabled else '🔴'
        return f"{status} {enabled} [{self.service_key}] {self.name} ({self.redis_host}:{self.redis_port})"
    
    def save(self, *args, **kwargs):
        """Ensure only one config is active at a time"""
        if self.is_active:
            # Deactivate all other configs
            CrawlCacheConfig.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_config(cls):
        """Get the currently active cache configuration"""
        try:
            return cls.objects.filter(is_active=True, enabled=True).first()
        except cls.DoesNotExist:
            return None
    
    def test_connection(self) -> tuple[bool, str]:
        """
        Test Redis connection.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            import redis
            client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password or None,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            client.ping()

            self.connection_status = 'connected'
            self.last_connection_test = timezone.now()
            self.save(update_fields=['connection_status', 'last_connection_test'])

            return True, f"Connected to Redis {self.redis_host}:{self.redis_port}"

        except Exception as exc:
            self.connection_status = 'failed'
            self.save(update_fields=['connection_status'])
            return False, f"Connection failed: {exc.__class__.__name__}: {exc}"


# ===== Redis-based Job Reset Rule (Status-only policy) =====

class JobResetRule(models.Model):
    """
    Status-only rule for resetting CrawlJob back to PENDING.
    Selection is flexible (all/domain/domain_regex/url_regex/rule_tag).
    """

    class SelectionType(models.TextChoices):
        ALL = 'all', 'All jobs'
        DOMAIN = 'domain', 'Exact domain'
        DOMAIN_REGEX = 'domain_regex', 'Domain regex'
        URL_REGEX = 'url_regex', 'URL regex'
        RULE = 'rule', 'Rule tag'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Tên rule (VD: 'Reset hourly - Amazon')")
    selection_type = models.CharField(max_length=20, choices=SelectionType.choices, default=SelectionType.ALL)
    rule_tag = models.CharField(max_length=100, blank=True)
    domain = models.ForeignKey('products_shared.Domain', on_delete=models.CASCADE, null=True, blank=True)
    domain_regex = models.CharField(max_length=255, blank=True)
    url_pattern = models.CharField(max_length=500, blank=True)

    frequency_hours = models.IntegerField(default=24, help_text="Thời gian reset về PENDING (giờ)")
    enabled = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'job_reset_rule'
        verbose_name = 'Job Reset Rule'
        verbose_name_plural = 'Job Reset Rules'
        ordering = ['-enabled', 'name']
        indexes = [
            models.Index(fields=['enabled', 'selection_type']),
        ]

    def __str__(self):
        target = {
            self.SelectionType.ALL: 'All jobs',
            self.SelectionType.DOMAIN: self.domain.name if self.domain else 'domain:—',
            self.SelectionType.DOMAIN_REGEX: f"domain~{self.domain_regex or '—'}",
            self.SelectionType.URL_REGEX: f"url~{self.url_pattern or '—'}",
            self.SelectionType.RULE: f"rule:{self.rule_tag or '—'}",
        }.get(self.selection_type, 'unknown')
        return f"{self.name} [{target}] every {self.frequency_hours}h"

    @classmethod
    def enabled_rules(cls):
        return list(cls.objects.filter(enabled=True).order_by('created_at'))

    def matches_job(self, job: CrawlJob) -> bool:
        product_url = getattr(job, 'product_url', None)
        domain = getattr(product_url, 'domain', None) if product_url else None
        domain_name = getattr(domain, 'name', None)
        url = getattr(product_url, 'normalized_url', None) or getattr(product_url, 'raw_url', None)
        job_rule_tag = getattr(job, 'rule_tag', None)

        if not self.enabled:
            return False
        if self.selection_type == self.SelectionType.ALL:
            return True
        if self.selection_type == self.SelectionType.DOMAIN:
            return bool(self.domain and domain_name and self.domain.name == domain_name)
        if self.selection_type == self.SelectionType.DOMAIN_REGEX:
            if not self.domain_regex or not domain_name:
                return False
            import re
            try:
                return bool(re.search(self.domain_regex, domain_name))
            except re.error:
                return False
        if self.selection_type == self.SelectionType.URL_REGEX:
            if not self.url_pattern or not url:
                return False
            import re
            try:
                return bool(re.search(self.url_pattern, url))
            except re.error:
                return False
        if self.selection_type == self.SelectionType.RULE:
            return bool(self.rule_tag and job_rule_tag and self.rule_tag == job_rule_tag)
        return False

    @classmethod
    def match_for_job(cls, job: CrawlJob) -> 'JobResetRule|None':
        for rule in cls.enabled_rules():
            if rule.matches_job(job):
                return rule
        return None
