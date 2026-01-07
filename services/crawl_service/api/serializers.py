"""
API Serializers - Data Transfer Objects

Serializers handle validation and conversion between 
HTTP requests/responses and domain objects.

State machine context:
- BotPullRequestSerializer: Request to pull PENDING jobs
- JobResponseSerializer: Response with job details to execute
- CrawlResultSubmissionSerializer: Bot submits result (success or failure)
- ResultResponseSerializer: Response after result creation
"""

from rest_framework import serializers
from decimal import Decimal


class BotPullRequestSerializer(serializers.Serializer):
    """
    Serializer for bot job pull request.
    Bot requests available PENDING jobs to execute.
    """
    bot_id = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Unique bot identifier"
    )
    max_jobs = serializers.IntegerField(
        default=10,
        min_value=1,
        max_value=100,
        required=False,
        help_text="Max number of jobs to pull (default: 10)"
    )
    domain = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Optional: filter by domain (e.g., 'example.com')"
    )


class JobResponseSerializer(serializers.Serializer):
    """
    Serializer for job response to bot.
    Contains job details for execution.
    """
    job_id = serializers.UUIDField(help_text="Unique job ID")
    url = serializers.URLField(help_text="URL to crawl")
    priority = serializers.IntegerField(help_text="Execution priority (1-20)")
    max_retries = serializers.IntegerField(help_text="Max retry attempts")
    timeout_seconds = serializers.IntegerField(help_text="Execution timeout in seconds")
    retry_count = serializers.IntegerField(help_text="Current retry count")
    locked_until = serializers.DateTimeField(help_text="Lock expires at (ISO 8601)")


class CrawlResultSubmissionSerializer(serializers.Serializer):
    """
    Serializer for bot result submission.
    Bot submits crawl result (success) or error (failure).
    
    Success submission:
    {
        "bot_id": "bot-001",
        "job_id": "uuid",
        "success": true,
        "price": 99.99,
        "currency": "USD",
        "title": "Product",
        "in_stock": true,
        "parsed_data": {...},
        "raw_html": "<html>..."
    }
    
    Failure submission:
    {
        "bot_id": "bot-001",
        "job_id": "uuid",
        "success": false,
        "error_msg": "Timeout: page didn't load"
    }
    """
    bot_id = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Bot ID that executed the job"
    )
    job_id = serializers.UUIDField(
        required=True,
        help_text="Job ID being submitted"
    )
    success = serializers.BooleanField(
        required=True,
        help_text="Whether crawl succeeded"
    )
    
    # Success fields (required if success=True)
    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=Decimal('0.00'),
        help_text="Extracted product price"
    )
    currency = serializers.CharField(
        max_length=3,
        required=False,
        allow_null=True,
        help_text="Currency code (USD, VND, EUR, etc.)"
    )
    title = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Product title/name"
    )
    in_stock = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Product availability"
    )
    raw_html = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Raw HTML snippet (optional, for debugging)"
    )
    parsed_data = serializers.JSONField(
        default=dict,
        required=False,
        help_text="Full parsed data from crawler"
    )
    
    # Failure fields (required if success=False)
    error_msg = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Error message if crawl failed"
    )
    
    def validate(self, data):
        """Validate based on success flag"""
        success = data.get('success')
        
        if success:
            # Success case: price and currency required
            if not data.get('price') or not data.get('currency'):
                raise serializers.ValidationError(
                    "price and currency are required when success=true"
                )
        else:
            # Failure case: error_msg optional but recommended
            pass
        
        return data
    
    def validate_currency(self, value):
        """Validate currency is 3-letter ISO code"""
        if value and len(value) != 3:
            raise serializers.ValidationError(
                "Currency must be 3-letter ISO code (e.g., USD, VND, EUR)"
            )
        return value.upper() if value else value


class ResultResponseSerializer(serializers.Serializer):
    """
    Serializer for result creation response (success case).
    """
    result_id = serializers.UUIDField(help_text="Unique result ID")
    job_id = serializers.UUIDField(help_text="Associated job ID")
    status = serializers.CharField(help_text="Job status after submission (done)")
    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Recorded price"
    )
    currency = serializers.CharField(help_text="Currency code")
    policy_next_run = serializers.DateTimeField(
        allow_null=True,
        help_text="When policy will next run (after rescheduling)"
    )


class JobRetryResponseSerializer(serializers.Serializer):
    """
    Serializer for retry response (failure case with retries remaining).
    Job auto-transitions to PENDING for retry.
    """
    job_id = serializers.UUIDField(help_text="Job ID")
    status = serializers.CharField(help_text="Job status (pending for retry)")
    retry_count = serializers.IntegerField(help_text="Current retry count")
    max_retries = serializers.IntegerField(help_text="Max retry attempts")
    message = serializers.CharField(help_text="Status message")


class JobFailedResponseSerializer(serializers.Serializer):
    """
    Serializer for failed response (retries exhausted).
    Job transitions to FAILED permanently.
    """
    job_id = serializers.UUIDField(help_text="Job ID")
    status = serializers.CharField(help_text="Job status (failed)")
    retry_count = serializers.IntegerField(help_text="Final retry count")
    max_retries = serializers.IntegerField(help_text="Max retry attempts")
    error = serializers.CharField(help_text="Error message from bot")
    message = serializers.CharField(help_text="Status message")
