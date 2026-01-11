"""
Django Admin Configuration for Crawl Service

Primary interface for managing crawl policies, jobs, and viewing results.
Integrated with CustomAdminSite for hash-protected access.

Admin Actions:
- CrawlPolicy: Sync jobs for domain, reset schedule
- CrawlJob: Sync all missing jobs, mark pending/expired, reset locks
"""

from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.urls import reverse, path
from django.db.models import Q, Count
from django.http import JsonResponse
import json

from ..models import CrawlJob, CrawlResult, BotConfig, JobResetRule
from core.admin_core.infrastructure.custom_admin import default_admin_site
import logging

logger = logging.getLogger(__name__)


class CrawlResultInline(admin.TabularInline):
    """Inline results for job"""
    model = CrawlResult
    extra = 0
    readonly_fields = ('price', 'currency', 'in_stock', 'title', 'crawled_at', 'created_at')
    can_delete = False
    fields = ('price', 'currency', 'title', 'in_stock', 'crawled_at')
    
    def has_add_permission(self, request, obj=None):
        return False

class JobResetRuleAdmin(admin.ModelAdmin):
    """Admin for status-only Job Reset Rules (Redis-backed)."""

    list_display = (
        'name', 'selection_badge', 'target_badge', 'frequency_badge', 'enabled', 'matching_jobs'
    )
    list_filter = ('enabled', 'selection_type',)
    search_fields = ('name', 'rule_tag', 'domain__name', 'domain_regex', 'url_pattern')
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Identification', {'fields': ('id', 'name', 'enabled')}),
        ('Selection', {'fields': ('selection_type', 'domain', 'domain_regex', 'url_pattern', 'rule_tag')}),
        ('Behaviour', {'fields': ('frequency_hours',)}),
        ('Metadata', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    ordering = ['-enabled', 'name']
    actions = ['schedule_resets_now']

    def selection_badge(self, obj):
        return obj.selection_type
    selection_badge.short_description = 'Selection'

    def target_badge(self, obj):
        if obj.selection_type == obj.SelectionType.DOMAIN and obj.domain:
            return format_html('<span style="background:#e3f2fd; padding:2px 6px; border-radius:3px;">{}</span>', obj.domain.name)
        if obj.selection_type == obj.SelectionType.DOMAIN_REGEX and obj.domain_regex:
            return format_html('<code>{}</code>', obj.domain_regex)
        if obj.selection_type == obj.SelectionType.URL_REGEX and obj.url_pattern:
            return format_html('<code>{}</code>', obj.url_pattern)
        if obj.selection_type == obj.SelectionType.RULE and obj.rule_tag:
            return format_html('<span style="background:#e8f5e9; padding:2px 6px; border-radius:3px;">{}</span>', obj.rule_tag)
        return 'All jobs'
    target_badge.short_description = 'Target'

    def frequency_badge(self, obj):
        return f"{obj.frequency_hours}h"
    frequency_badge.short_description = 'Frequency'

    def matching_jobs(self, obj):
        qs = CrawlJob.objects.filter(status='done')
        if obj.selection_type == obj.SelectionType.DOMAIN and obj.domain:
            qs = qs.filter(product_url__domain=obj.domain)
        elif obj.selection_type == obj.SelectionType.DOMAIN_REGEX and obj.domain_regex:
            qs = qs.filter(product_url__domain__name__regex=obj.domain_regex)
        elif obj.selection_type == obj.SelectionType.URL_REGEX and obj.url_pattern:
            qs = qs.filter(product_url__normalized_url__regex=obj.url_pattern)
        elif obj.selection_type == obj.SelectionType.RULE and obj.rule_tag:
            qs = qs.filter(rule_tag=obj.rule_tag)
        return qs.count()
    matching_jobs.short_description = 'Matching DONE jobs'

    @admin.action(description="🕒 Schedule Resets Now")
    def schedule_resets_now(self, request, queryset):
        from ..infrastructure.redis_job_scheduler import schedule_reset_to_pending
        total = 0
        for rule in queryset.filter(enabled=True):
            qs = CrawlJob.objects.filter(status='done')
            if rule.selection_type == rule.SelectionType.DOMAIN and rule.domain:
                qs = qs.filter(product_url__domain=rule.domain)
            elif rule.selection_type == rule.SelectionType.DOMAIN_REGEX and rule.domain_regex:
                qs = qs.filter(product_url__domain__name__regex=rule.domain_regex)
            elif rule.selection_type == rule.SelectionType.URL_REGEX and rule.url_pattern:
                qs = qs.filter(product_url__normalized_url__regex=rule.url_pattern)
            elif rule.selection_type == rule.SelectionType.RULE and rule.rule_tag:
                qs = qs.filter(rule_tag=rule.rule_tag)
            job_ids = list(qs.values_list('id', flat=True)[:2000])
            scheduled = schedule_reset_to_pending([str(j) for j in job_ids], run_at_ts=timezone.now().timestamp())
            total += scheduled
        self.message_user(request, f"✓ Scheduled {total} job(s) to PENDING via Redis")


class CrawlJobAdmin(admin.ModelAdmin):
    """Admin for Crawl Job - individual URL execution with state machine"""
    
    list_display = (
        'url_badge',
        'domain_badge',
        'rule_tag',
        'status_badge',
        'bot_badge',
        'priority_badge',
        'retry_info',
        'locked_info',
        'created_at',
    )
    
    list_filter = ('status', 'priority', 'rule_tag', 'product_url__domain__name', 'created_at', 'locked_at', 'policy')
    search_fields = ('product_url__normalized_url', 'locked_by', 'product_url__domain__name', 'rule_tag')
    readonly_fields = (
        'id',
        'product_url',
        'policy',
        'created_at',
        'updated_at',
        'state_machine_display',
        'lock_info_display',
        'error_display',
        'sync_status_display',
    )
    
    fieldsets = (
        ('URL & Identification', {
            'fields': ('id', 'product_url', 'policy'),
            'description': 'ProductURL references shared data via hash optimization'
        }),
        ('Sync Status', {
            'fields': ('sync_status_display',),
            'classes': ('collapse',)
        }),
        ('State Machine', {
            'fields': ('status', 'state_machine_display')
        }),
        ('Bot Locking', {
            'fields': ('locked_by', 'locked_at', 'lock_ttl_seconds', 'lock_info_display')
        }),
        ('Configuration', {
            'fields': ('priority', 'max_retries', 'timeout_minutes', 'rule_tag')
        }),
        ('Retry Tracking', {
            'fields': ('retry_count', 'last_error', 'error_display')
        }),
        ('Execution', {
            'fields': ('last_result_at',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-priority', '-created_at']
    actions = ['mark_pending', 'mark_expired', 'reset_lock', 'sync_all_missing_jobs']
    inlines = [CrawlResultInline]
    
    def get_queryset(self, request):
        """Optimize query with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('product_url', 'product_url__domain', 'policy')
    
    def url_badge(self, obj):
        """Display URL with truncation from ProductURL"""
        if obj.product_url:
            url = obj.product_url.normalized_url
            return format_html(
                '<a href="{}" target="_blank" title="{}">{}</a>',
                url, url, url[:60]
            )
        return '—'
    url_badge.short_description = 'URL'
    
    def domain_badge(self, obj):
        """Display domain name"""
        if obj.product_url and obj.product_url.domain:
            return format_html(
                '<span style="background: #e3f2fd; padding: 2px 6px; border-radius: 3px;">{}</span>',
                obj.product_url.domain.name
            )
        return '—'
    domain_badge.short_description = 'Domain'
    
    def sync_status_display(self, obj):
        """Display sync status between ProductURL and CrawlJob"""
        from services.products_shared.infrastructure.django_models import ProductURL
        
        # Count total ProductURLs
        total_urls = ProductURL.objects.filter(is_active=True).count()
        
        # Count jobs
        total_jobs = CrawlJob.objects.count()
        
        # Count URLs without jobs
        missing_jobs = ProductURL.objects.filter(
            is_active=True,
            crawl_jobs__isnull=True
        ).count()
        
        # Count jobs with deleted URLs (orphaned)
        orphaned_jobs = CrawlJob.objects.filter(
            product_url__isnull=True
        ).count()
        
        html = '<div style="background: #f5f5f5; padding: 15px; border-radius: 5px; font-family: monospace;">'
        html += '<h3 style="margin-top: 0;">📊 Sync Status</h3>'
        html += f'<p><b>Total Active ProductURLs:</b> {total_urls}</p>'
        html += f'<p><b>Total CrawlJobs:</b> {total_jobs}</p>'
        
        if missing_jobs > 0:
            html += f'<p style="color: #ff9800;"><b>⚠️ URLs without jobs:</b> {missing_jobs}</p>'
            html += '<p style="color: #999; font-size: 0.9em;">Use action "Sync All Missing Jobs" to create them</p>'
        else:
            html += '<p style="color: #4caf50;"><b>✓ All URLs have jobs</b></p>'
        
        if orphaned_jobs > 0:
            html += f'<p style="color: #f44336;"><b>⚠️ Orphaned jobs (deleted URLs):</b> {orphaned_jobs}</p>'
            html += '<p style="color: #999; font-size: 0.9em;">These will auto-delete due to CASCADE</p>'
        
        html += '</div>'
        return format_html(html)
    sync_status_display.short_description = 'Sync Status'
    
    def status_badge(self, obj):
        """Display status with color and emoji"""
        status_colors = {
            'pending': ('⏳ Pending', 'blue'),
            'locked': ('🔒 Locked', 'orange'),
            'done': ('✓ Done', 'green'),
            'failed': ('✗ Failed', 'red'),
            'expired': ('⏱️ Expired', 'red'),
        }
        label, color = status_colors.get(obj.status, ('Unknown', 'gray'))
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 6px; border-radius: 3px;">{}</span>',
            color, label
        )
    status_badge.short_description = 'Status'
    
    def bot_badge(self, obj):
        """Display bot ID if locked"""
        if obj.locked_by:
            return format_html('<span style="color: blue; font-weight: bold;">{}</span>', obj.locked_by)
        return "—"
    bot_badge.short_description = 'Bot'
    
    def priority_badge(self, obj):
        """Display priority"""
        priority_labels = {1: 'Low', 5: 'Normal', 10: 'High', 20: 'Urgent'}
        return priority_labels.get(obj.priority, '?')
    priority_badge.short_description = 'Priority'
    
    def retry_info(self, obj):
        """Display retry info"""
        if obj.retry_count >= obj.max_retries:
            return format_html('<span style="color: red;">Retries exhausted ({}/{})</span>', obj.retry_count, obj.max_retries)
        return f"{obj.retry_count}/{obj.max_retries}"
    retry_info.short_description = 'Retries'
    
    def locked_info(self, obj):
        """Display lock info"""
        if obj.status != 'locked':
            return "—"
        if obj.locked_at:
            elapsed = (timezone.now() - obj.locked_at).total_seconds()
            remaining = obj.lock_ttl_seconds - elapsed
            if remaining < 0:
                return format_html('<span style="color: red;">EXPIRED</span>')
            return f"{int(remaining)}s"
        return "—"
    locked_info.short_description = 'Lock TTL'
    
    def state_machine_display(self, obj):
        """Show state machine diagram"""
        states = ['pending', 'locked', 'done', 'failed', 'expired']
        current = obj.status
        html = '<div style="font-family: monospace; background: #f5f5f5; padding: 10px; border-radius: 3px;">'
        html += 'PENDING → LOCKED → DONE<br/>↓<br/>FAILED (if retries left → PENDING)<br/>EXPIRED (if TTL exceeded)<br><br>'
        html += f'<b>Current: <span style="color: #2196F3;">{current.upper()}</span></b>'
        html += '</div>'
        return format_html(html)
    state_machine_display.short_description = 'State Machine'
    
    def lock_info_display(self, obj):
        """Show lock info"""
        if obj.status != 'locked':
            return "Not locked"
        html = f'<b>Locked by:</b> {obj.locked_by}<br/>'
        if obj.locked_at:
            elapsed = (timezone.now() - obj.locked_at).total_seconds()
            remaining = obj.lock_ttl_seconds - elapsed
            html += f'<b>TTL:</b> {obj.lock_ttl_seconds}s<br/>'
            html += f'<b>Elapsed:</b> {int(elapsed)}s<br/>'
            html += f'<b>Remaining:</b> {int(remaining)}s<br/>'
            if remaining < 0:
                html += '<span style="color: red; font-weight: bold;">⚠️ LOCK EXPIRED</span>'
        return format_html(html)
    lock_info_display.short_description = 'Lock Details'
    
    def error_display(self, obj):
        """Show error info"""
        if not obj.last_error:
            return "No errors"
        return f"{obj.last_error[:200]}"
    error_display.short_description = 'Last Error'
    
    @admin.action(description="🔄 Sync All Missing Jobs from ProductURLs")
    def sync_all_missing_jobs(self, request, queryset):
        """Create jobs for all ProductURLs that don't have jobs yet"""
        from services.products_shared.infrastructure.django_models import ProductURL
        from django.db import transaction
        
        # Get all active ProductURLs without jobs
        product_urls = ProductURL.objects.filter(
            is_active=True,
            crawl_jobs__isnull=True
        ).select_related('domain')
        
        total_urls = product_urls.count()
        total_created = 0
        total_failed = 0
        
        for product_url in product_urls:
            try:
                with transaction.atomic():
                    CrawlJob.objects.create(
                        product_url=product_url,
                        status='pending',
                        priority=5,
                        max_retries=3,
                        timeout_minutes=10,
                        lock_ttl_seconds=600,
                        rule_tag='base'
                    )
                    total_created += 1
            except Exception as e:
                total_failed += 1
                logger.error(f"Failed to create job for {product_url.normalized_url}: {e}")
        
        self.message_user(
            request,
            f"✓ Synced {total_urls} ProductURLs: created {total_created} jobs, {total_failed} failed"
        )
    
    @admin.action(description="Mark as Pending")
    def mark_pending(self, request, queryset):
        """Reset job status to PENDING for re-execution"""
        updated = queryset.update(
            status='pending',
            locked_by=None,
            locked_at=None
        )
        self.message_user(request, f"✓ {updated} jobs marked as PENDING")
    
    @admin.action(description="Mark as Expired")
    def mark_expired(self, request, queryset):
        """Mark LOCKED jobs as EXPIRED"""
        updated = queryset.filter(status='locked').update(
            status='expired',
            locked_by=None,
            locked_at=None
        )
        self.message_user(request, f"✓ {updated} jobs marked as EXPIRED")
    
    @admin.action(description="Reset Lock")
    def reset_lock(self, request, queryset):
        """Release locks for LOCKED jobs"""
        updated = queryset.filter(status='locked').update(
            locked_by=None,
            locked_at=None,
            status='pending'
        )
        self.message_user(request, f"✓ Released locks on {updated} jobs")
    
    def has_delete_permission(self, request, obj=None):
        # Only allow delete if not LOCKED
        if obj and obj.status == 'locked':
            return False
        return request.user.is_superuser


class CrawlResultAdmin(admin.ModelAdmin):
    """Admin for Crawl Result - outcomes from bot execution"""
    
    list_display = (
        'job_url',
        'job_status_badge',
        'job_last_error',
        'price_display',
        'price_sources_badge',
        'stock_badge',
        'crawled_ago',
        'created_at',
    )
    
    list_filter = ('currency', 'in_stock', 'created_at', 'crawled_at')
    search_fields = ('job__product_url__normalized_url', 'job__locked_by', 'title')
    readonly_fields = (
        'id',
        'job_display',
        'price',
        'currency',
        'title',
        'in_stock',
        'crawled_at',
        'created_at',
        'parsed_data_display',
        'raw_html',
    )
    
    fieldsets = (
        ('Result Identification', {
            'fields': ('id', 'job_display', 'created_at')
        }),
        ('Price Information', {
            'fields': ('price', 'currency')
        }),
        ('Product Information', {
            'fields': ('title', 'in_stock')
        }),
        ('Crawl Details', {
            'fields': ('crawled_at',)
        }),
        ('Parser Data', {
            'fields': ('parsed_data_display', 'raw_html'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-created_at']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('job', 'job__product_url')
    
    def job_url(self, obj):
        """Display job URL from ProductURL"""
        if obj.job and obj.job.product_url:
            return obj.job.product_url.normalized_url[:60]
        return '—'
    job_url.short_description = 'URL'

    def job_display(self, obj):
        """Display job with link to detail page"""
        if not obj.job:
            return '—'
        url = reverse('admin:crawl_service_crawljob_change', args=[obj.job.id])
        job_url = obj.job.product_url.normalized_url[:50] if obj.job.product_url else 'N/A'
        status_emoji = {
            'pending': '⏳',
            'locked': '🔒',
            'done': '✓',
            'failed': '✗',
            'expired': '⏱️'
        }.get(obj.job.status, '?')
        return format_html(
            '<a href="{}">{} {} ({})</a>',
            url,
            status_emoji,
            job_url,
            obj.job.status
        )
    job_display.short_description = 'Job'

    def price_sources_badge(self, obj):
        """Display price extraction sources with confidence for ML"""
        if not obj.parsed_data:
            return '—'
        
        pd = obj.parsed_data
        price_sources = pd.get('price_sources', [])
        price_extraction = pd.get('price_extraction', {})
        
        if not price_sources:
            return format_html('<span style="color:#999;">No sources</span>')
        
        # Source mapping to extraction keys
        source_map = {
            'jsonld': ('extract_price_from_jsonld', '#4CAF50', 'JSON-LD'),
            'og': ('extract_price_from_og', '#2196F3', 'OG'),
            'microdata': ('extract_price_from_microdata', '#9C27B0', 'Micro'),
            'script_data': ('extract_price_from_script_data', '#FF9800', 'Script'),
            'html_ml': ('extract_price_from_html_ml', '#E91E63', 'ML'),
        }
        
        badges = []
        for source in price_sources:
            if source not in source_map:
                badges.append('<span style="background:#777;color:white;padding:2px 6px;border-radius:3px;margin-right:3px;font-size:11px;">{}</span>'.format(source))
                continue
                
            extract_key, color, label = source_map[source]
            
            # Get confidence for ML source
            if source == 'html_ml' and extract_key in price_extraction:
                confidence = price_extraction[extract_key].get('confidence', 0.0)
                badges.append(
                    '<span style="background:{};color:white;padding:2px 6px;border-radius:3px;margin-right:3px;font-size:11px;font-weight:bold;">{} {:.3f}</span>'.format(
                        color, label, confidence
                    )
                )
            else:
                badges.append(
                    '<span style="background:{};color:white;padding:2px 6px;border-radius:3px;margin-right:3px;font-size:11px;">{}</span>'.format(
                        color, label
                    )
                )
        
        return format_html(''.join(badges))
    price_sources_badge.short_description = 'Sources'

    def job_status_badge(self, obj):
        """Display job status badge"""
        status_colors = {
            'pending': ('⏳ Pending', '#2196F3'),
            'locked': ('🔒 Locked', '#FF9800'),
            'done': ('✓ Done', '#4CAF50'),
            'failed': ('✗ Failed', '#F44336'),
            'expired': ('⏱️ Expired', '#E91E63'),
        }
        label, color = status_colors.get(obj.job.status, ('Unknown', '#9E9E9E'))
        return format_html(
            '<span style="background:{};color:white;padding:2px 6px;border-radius:3px;">{}</span>',
            color,
            label,
        )
    job_status_badge.short_description = 'Job Status'

    def job_last_error(self, obj):
        """Show last error from job"""
        if not obj.job.last_error:
            return '—'
        return obj.job.last_error[:120]
    job_last_error.short_description = 'Last Error'
    
    def price_display(self, obj):
        """Display price with currency"""
        return f"{obj.price} {obj.currency}"
    price_display.short_description = 'Price'
    
    def stock_badge(self, obj):
        """Display stock status"""
        if obj.in_stock:
            return format_html('<span style="color: green;">✓ In Stock</span>')
        return format_html('<span style="color: red;">✗ Out of Stock</span>')
    stock_badge.short_description = 'Stock'
    
    def crawled_ago(self, obj):
        """Display how long ago crawled"""
        delta = timezone.now() - obj.crawled_at
        minutes = delta.total_seconds() / 60
        if minutes < 60:
            return f"{int(minutes)} min ago"
        hours = minutes / 60
        if hours < 24:
            return f"{int(hours)}h ago"
        days = hours / 24
        return f"{int(days)}d ago"
    crawled_ago.short_description = 'Crawled'
    
    def parsed_data_display(self, obj):
        """Display parsed data with detailed price extraction sources"""
        if not obj.parsed_data:
            return "No data"

        pd = obj.parsed_data or {}
        price = pd.get('price') or pd.get('price_value')
        currency = pd.get('currency') or pd.get('currency_code')
        price_formatted = pd.get('price_formatted')
        confidence = pd.get('confidence')
        price_sources = pd.get('price_sources') or []
        price_extraction = pd.get('price_extraction') or {}
        source_url = pd.get('source_url')

        parts = []
        parts.append('<div style="background:#f8f9fa;border:1px solid #e0e0e0;border-radius:6px;padding:12px;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">')
        
        # Summary section
        parts.append('<div style="margin-bottom:12px;padding-bottom:10px;border-bottom:2px solid #e0e0e0;">')
        parts.append('<h4 style="margin:0 0 8px 0;color:#333;">📊 Extraction Summary</h4>')
        
        if price is not None:
            parts.append('<span style="background:#4CAF50;color:white;padding:4px 8px;border-radius:4px;font-weight:bold;">💰 {}</span>'.format(price))
        if currency:
            parts.append('<span style="background:#2196F3;color:white;padding:4px 8px;border-radius:4px;margin-left:6px;font-weight:bold;">💱 {}</span>'.format(currency))
        if price_formatted:
            parts.append('<span style="background:#607D8B;color:white;padding:4px 8px;border-radius:4px;margin-left:6px;">🧾 {}</span>'.format(price_formatted))
        if confidence is not None:
            conf_color = '#4CAF50' if confidence >= 0.85 else '#FF9800' if confidence >= 0.5 else '#F44336'
            parts.append('<span style="background:{};color:white;padding:4px 8px;border-radius:4px;margin-left:6px;font-weight:bold;">🔬 {:.4f}</span>'.format(conf_color, confidence))
        
        if price_sources:
            parts.append('<div style="margin-top:8px;color:#555;font-size:13px;">')
            parts.append('<b>Active sources:</b> ')
            for src in price_sources:
                parts.append('<code style="background:#E3F2FD;color:#1976D2;padding:2px 6px;border-radius:3px;margin-right:4px;">{}</code>'.format(src))
            parts.append('</div>')
        
        if source_url:
            parts.append('<div style="margin-top:6px;color:#777;font-size:12px;">🔗 {}</div>'.format(source_url[:80]))
        
        parts.append('</div>')

        # Detailed extraction sources
        if price_extraction:
            parts.append('<div style="margin-top:12px;">')
            parts.append('<h4 style="margin:0 0 10px 0;color:#333;">🔍 Price Extraction Details</h4>')
            
            # Source display order and labels
            source_info = [
                ('extract_price_from_jsonld', 'JSON-LD', '🏆', '#4CAF50'),
                ('extract_price_from_og', 'Open Graph', '🌐', '#2196F3'),
                ('extract_price_from_microdata', 'Microdata', '📋', '#9C27B0'),
                ('extract_price_from_script_data', 'Script Data', '📜', '#FF9800'),
                ('extract_price_from_html_ml', 'HTML ML', '🤖', '#E91E63'),
            ]
            
            for source_key, label, emoji, color in source_info:
                if source_key not in price_extraction:
                    continue
                    
                data = price_extraction[source_key]
                src_price = data.get('price')
                src_currency = data.get('currency')
                src_confidence = data.get('confidence', 0.0)
                
                # Determine if source found data
                has_data = src_price is not None and src_price != 0
                bg_color = '#fff' if has_data else '#f5f5f5'
                border_color = color if has_data else '#ddd'
                
                parts.append('<div style="background:{};border-left:4px solid {};padding:8px 10px;margin-bottom:8px;border-radius:4px;">'.format(bg_color, border_color))
                parts.append('<div style="display:flex;align-items:center;justify-content:space-between;">')
                
                # Source name
                parts.append('<div style="flex:1;">')
                parts.append('<span style="font-weight:bold;color:{};font-size:14px;">{} {}</span>'.format(color, emoji, label))
                parts.append('</div>')
                
                # Data values
                parts.append('<div style="flex:2;text-align:right;">')
                if has_data:
                    parts.append('<span style="color:#333;font-weight:bold;margin-right:12px;">{} {}</span>'.format(
                        src_price if src_price else '—',
                        src_currency if src_currency else ''
                    ))
                    # Confidence badge
                    if src_confidence >= 0.85:
                        conf_badge_color = '#4CAF50'
                        conf_label = 'High'
                    elif src_confidence >= 0.5:
                        conf_badge_color = '#FF9800'
                        conf_label = 'Medium'
                    else:
                        conf_badge_color = '#F44336'
                        conf_label = 'Low'
                    parts.append('<span style="background:{};color:white;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:bold;">{} ({:.4f})</span>'.format(
                        conf_badge_color, conf_label, src_confidence
                    ))
                else:
                    parts.append('<span style="color:#999;font-style:italic;">No data</span>')
                    if src_confidence == 0.0:
                        parts.append('<span style="background:#E0E0E0;color:#666;padding:2px 8px;border-radius:12px;font-size:11px;margin-left:8px;">0.0000</span>')
                
                parts.append('</div>')
                parts.append('</div>')
                parts.append('</div>')
            
            parts.append('</div>')

        # Full JSON (collapsed)
        parts.append('<details style="margin-top:12px;">')
        parts.append('<summary style="cursor:pointer;color:#1976D2;font-weight:bold;font-size:13px;">📄 View Full JSON</summary>')
        # Escape JSON to prevent format_html interpretation of curly braces
        json_str = json.dumps(pd, indent=2, ensure_ascii=False)
        json_str_escaped = json_str.replace('{', '{{').replace('}', '}}')
        parts.append('<pre style="margin-top:8px;background:#263238;color:#AED581;padding:12px;border-radius:4px;overflow-x:auto;font-size:12px;">{}</pre>'.format(
            json_str_escaped
        ))
        parts.append('</details>')
        
        parts.append('</div>')
        return mark_safe(''.join(parts))
    parsed_data_display.short_description = 'Parsed Data'
    
    def has_add_permission(self, request):
        # Results created only via API
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Results should be kept for audit trail
        return False


class BotConfigAdmin(admin.ModelAdmin):
    """Admin for Bot Configuration - manage bot authentication and settings"""
    
    list_display = (
        'bot_status_badge',
        'bot_id',
        'name',
        'token_preview',
        'max_jobs_per_pull',
        'custom_ttl_display',
        'success_rate_display',
        'stats_display',
        'last_pull_at',
    )
    
    list_filter = ('enabled', 'created_at', 'last_pull_at')
    search_fields = ('bot_id', 'name', 'description')
    readonly_fields = (
        'id',
        'token_display',
        'total_jobs_pulled',
        'total_jobs_completed',
        'total_jobs_failed',
        'last_pull_at',
        'last_submit_at',
        'created_at',
        'updated_at',
        'success_rate_display',
    )
    
    fieldsets = (
        ('Bot Identification', {
            'fields': ('id', 'bot_id', 'name', 'description')
        }),
        ('Authentication', {
            'fields': ('token_display', 'enabled'),
            'description': 'API Token is auto-generated. Use "Regenerate API Token" action to create new token.'
        }),
        ('Configuration', {
            'fields': (
                'max_jobs_per_pull',
                'custom_lock_ttl_seconds',
                'rate_limit_per_minute',
                'priority_boost',
            )
        }),
        ('Domain Filtering', {
            'fields': ('allowed_domains',),
            'description': 'List of domains this bot can crawl. Leave empty to allow all domains.'
        }),
        ('Statistics', {
            'fields': (
                'total_jobs_pulled',
                'total_jobs_completed',
                'total_jobs_failed',
                'success_rate_display',
                'last_pull_at',
                'last_submit_at',
            ),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-enabled', 'bot_id']
    
    def bot_status_badge(self, obj):
        """Display bot status with badge"""
        if obj.enabled:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-weight: bold;">✓ ENABLED</span>'
            )
        return format_html(
            '<span style="background: #dc3545; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">✗ DISABLED</span>'
        )
    bot_status_badge.short_description = 'Status'
    
    def custom_ttl_display(self, obj):
        """Display custom TTL or default"""
        if obj.custom_lock_ttl_seconds:
            return format_html(
                '<span style="background: #17a2b8; color: white; padding: 2px 6px; '
                'border-radius: 3px;">{} sec</span>',
                obj.custom_lock_ttl_seconds
            )
        return format_html(
            '<span style="color: #6c757d;">600 sec (default)</span>'
        )
    custom_ttl_display.short_description = 'Lock TTL'
    
    def success_rate_display(self, obj):
        """Display success rate with color coding"""
        rate = obj.success_rate()
        if rate >= 80:
            color = '#28a745'  # Green
        elif rate >= 50:
            color = '#ffc107'  # Yellow
        else:
            color = '#dc3545'  # Red
        
        rate_formatted = "{:.1f}".format(rate)
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-weight: bold;">{}%</span>',
            color, rate_formatted
        )
    success_rate_display.short_description = 'Success Rate'
    
    def stats_display(self, obj):
        """Display job statistics"""
        completed = obj.total_jobs_completed
        failed = obj.total_jobs_failed
        total = obj.total_jobs_pulled
        return format_html(
            '<span style="color: #28a745;">✓ {}</span> | '
            '<span style="color: #dc3545;">✗ {}</span> | '
            '<span style="color: #6c757d;">Total: {}</span>',
            completed,
            failed,
            total
        )
    stats_display.short_description = 'Stats (✓/✗/Total)'
    
    def token_preview(self, obj):
        """Show truncated token in list view"""
        if not obj.api_token:
            return format_html('<span style="color: #dc3545;">Not set</span>')
        
        token_preview = obj.api_token[:20] + '...'
        return format_html(
            '<code style="background: #f8f9fa; padding: 2px 6px; border-radius: 3px;">{}</code>',
            token_preview
        )
    token_preview.short_description = 'API Token'
    
    def token_display(self, obj):
        """Show full token in detail view with copy button"""
        if not obj.api_token:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">⚠ No API Token Set</span><br>'
                '<small>Token will be auto-generated on save</small>'
            )
        
        return format_html(
            '<div style="background: #f8f9fa; padding: 10px; border-radius: 4px; border: 1px solid #dee2e6;">'
            '<code style="font-size: 14px; word-break: break-all;">{}</code>'
            '<br><br>'
            '<button type="button" onclick="navigator.clipboard.writeText(\'{}\'); '
            'alert(\'Token copied to clipboard!\');" '
            'style="background: #007bff; color: white; border: none; padding: 6px 12px; '
            'border-radius: 4px; cursor: pointer;">📋 Copy Token</button>'
            '<br><small style="color: #6c757d; margin-top: 8px; display: block;">'
            'Use "Regenerate API Token" action to create a new token (invalidates old one)</small>'
            '</div>',
            obj.api_token,
            obj.api_token
        )
    token_display.short_description = 'API Token'
    
    actions = ['enable_bots', 'disable_bots', 'reset_stats', 'regenerate_token']
    
    def enable_bots(self, request, queryset):
        """Enable selected bots"""
        count = queryset.update(enabled=True)
        self.message_user(request, f'{count} bot(s) enabled')
    enable_bots.short_description = 'Enable selected bots'
    
    def disable_bots(self, request, queryset):
        """Disable selected bots"""
        count = queryset.update(enabled=False)
        self.message_user(request, f'{count} bot(s) disabled')
    disable_bots.short_description = 'Disable selected bots'
    
    def reset_stats(self, request, queryset):
        """Reset bot statistics"""
        for bot in queryset:
            bot.total_jobs_pulled = 0
            bot.total_jobs_completed = 0
            bot.total_jobs_failed = 0
            bot.last_pull_at = None
            bot.last_submit_at = None
            bot.save()
        self.message_user(request, f'Statistics reset for {queryset.count()} bot(s)')
    reset_stats.short_description = 'Reset statistics'
    
    def regenerate_token(self, request, queryset):
        """Regenerate API tokens for selected bots"""
        import secrets
        count = 0
        for bot in queryset:
            # Generate new token
            bot.api_token = f"bot_{bot.bot_id}_{secrets.token_urlsafe(32)}"
            bot.save(update_fields=['api_token'])
            count += 1
            logger.info(f"Regenerated API token for bot: {bot.bot_id}")
        
        self.message_user(
            request,
            f'API tokens regenerated for {count} bot(s). '
            'Old tokens are now invalid. Update bots with new tokens.',
            level='WARNING'
        )
    regenerate_token.short_description = '🔄 Regenerate API Token (invalidates old token)'


class CrawlCacheConfigAdmin(admin.ModelAdmin):
    """Admin for Cache Configuration - Redis settings"""
    
    list_display = (
        'name',
        'service_key',
        'status_badge',
        'connection_badge',
        'redis_connection_display',
        'ttl_display',
        'is_active',
        'last_connection_test',
    )
    
    list_filter = ('enabled', 'is_active', 'connection_status', 'created_at')
    search_fields = ('name', 'redis_host')
    readonly_fields = (
        'id',
        'service_key',
        'connection_status',
        'last_connection_test',
        'created_at',
        'updated_at',
        'connection_test_display',
    )
    
    fieldsets = (
        ('Configuration Name', {
            'fields': ('id', 'service_key', 'name'),
        }),
        ('Redis Connection', {
            'fields': (
                'redis_host',
                'redis_port',
                'redis_db',
                'redis_password',
            ),
            'description': 'Redis server connection settings'
        }),
        ('Cache Behavior', {
            'fields': (
                'enabled',
                'is_active',
                'default_ttl_seconds',
            ),
            'description': 'Global cache settings'
        }),
        ('Cache Strategies', {
            'fields': (
                'cache_pending_jobs',
                'cache_job_details',
                'cache_product_urls',
            ),
            'description': 'Enable/disable specific caching strategies'
        }),
        ('TTL Overrides', {
            'fields': (
                'pending_jobs_ttl_seconds',
                'job_details_ttl_seconds',
                'product_urls_ttl_seconds',
            ),
            'description': 'Custom TTL for each cache type'
        }),
        ('Connection Status', {
            'fields': (
                'connection_status',
                'last_connection_test',
                'connection_test_display',
            ),
            'description': 'Redis connection health'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-is_active', '-created_at']
    actions = ['test_connection', 'activate_config', 'clear_all_cache', 'disable_cache']

    def has_add_permission(self, request):
        """Allow up to predefined service slots (max 3)."""
        from ..models import CrawlCacheConfig
        return CrawlCacheConfig.objects.count() < 3
    
    def get_urls(self):
        """Add custom URL for test connection endpoint."""
        from django.urls import re_path
        custom_urls = [
            re_path(
                r'^(?P<object_id>[a-f0-9-]+)/test/$',
                self.admin_site.admin_view(self.test_connection_view),
                name='crawlcacheconfig_test_connection',
            ),
        ]
        urls = super().get_urls()
        return custom_urls + urls  # Put custom URLs BEFORE standard ones
    
    def test_connection_view(self, request, object_id):
        """AJAX view to test Redis connection."""
        from ..models import CrawlCacheConfig
        
        # Only allow GET or POST
        if request.method not in ['GET', 'POST']:
            return JsonResponse({
                'success': False,
                'message': 'Method not allowed',
            }, status=405)
        
        try:
            config = CrawlCacheConfig.objects.get(id=object_id)
            success, message = config.test_connection()
            
            # Update object after test
            config.refresh_from_db()
            
            return JsonResponse({
                'success': success,
                'message': message,
                'status': config.connection_status,
                'last_test': config.last_connection_test.isoformat() if config.last_connection_test else None,
            }, status=200, content_type='application/json')
        except CrawlCacheConfig.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Configuration not found',
            }, status=404, content_type='application/json')
        except Exception as e:
            logger.error(f"Error testing connection: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}',
            }, status=500, content_type='application/json')
    
    def status_badge(self, obj):
        """Display enabled/disabled status"""
        if obj.enabled:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-weight: bold;">🟢 ENABLED</span>'
            )
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">🔴 DISABLED</span>'
        )
    status_badge.short_description = 'Status'
    
    def connection_badge(self, obj):
        """Display connection status badge"""
        if obj.connection_status == 'connected':
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px;">✓ Connected</span>'
            )
        elif obj.connection_status == 'failed':
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 3px 8px; '
                'border-radius: 3px;">✗ Failed</span>'
            )
        else:
            return format_html(
                '<span style="background: #ffc107; color: black; padding: 3px 8px; '
                'border-radius: 3px;">? Untested</span>'
            )
    connection_badge.short_description = 'Connection'
    
    def redis_connection_display(self, obj):
        """Display Redis connection string"""
        return format_html(
            '<code style="background: #f8f9fa; padding: 2px 6px; border-radius: 3px;">'
            '{}:{} (db={})</code>',
            obj.redis_host,
            obj.redis_port,
            obj.redis_db
        )
    redis_connection_display.short_description = 'Redis Server'
    
    def ttl_display(self, obj):
        """Display TTL settings"""
        return format_html(
            '<span style="font-size: 12px;">'
            'Default: {}s | Jobs: {}s | Details: {}s | URLs: {}s'
            '</span>',
            obj.default_ttl_seconds,
            obj.pending_jobs_ttl_seconds,
            obj.job_details_ttl_seconds,
            obj.product_urls_ttl_seconds
        )
    ttl_display.short_description = 'TTL Settings'
    
    def connection_test_display(self, obj):
        """Display connection test button and results"""
        test_btn = format_html(
            '<button type="button" onclick="testRedisConnection(\'{}\');" '
            'style="background: #007bff; color: white; border: none; padding: 8px 16px; '
            'border-radius: 4px; cursor: pointer; font-weight: bold;">🔌 Test Connection Now</button>',
            obj.id
        )
        
        if obj.last_connection_test:
            last_test = format_html(
                '<div style="margin-top: 10px; padding: 10px; background: #f8f9fa; '
                'border-radius: 4px; border-left: 4px solid {};">'
                '<strong>Last Test:</strong> {}<br>'
                '<strong>Status:</strong> {}'
                '</div>',
                '#28a745' if obj.connection_status == 'connected' else '#dc3545',
                obj.last_connection_test.strftime('%Y-%m-%d %H:%M:%S'),
                obj.get_connection_status_display()
            )
        else:
            last_test = format_html(
                '<div style="margin-top: 10px; color: #6c757d; font-style: italic;">'
                'No connection test performed yet'
                '</div>'
            )
        
        script = format_html(
            '<script>'
            'function testRedisConnection(configId) {{'
            '  if (!confirm("Test Redis connection now?")) return;'
            '  var csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");'
            '  var token = csrfToken ? csrfToken.value : "";'
            '  var testUrl = window.location.pathname.replace(/\\/change\\/?$/, "/") + "test/";'
            '  fetch(testUrl, {{'
            '    method: "POST",'
            '    headers: {{'
            '      "Content-Type": "application/json",'
            '      "X-CSRFToken": token,'
            '      "X-Requested-With": "XMLHttpRequest"'
            '    }}'
            '  }})'
            '  .then(function(response) {{'
            '    if (!response.ok) {{'
            '      throw new Error("HTTP " + response.status + " - " + response.statusText);'
            '    }}'
            '    return response.json();'
            '  }})'
            '  .then(function(data) {{'
            '    console.log("Response:", data);'
            '    if (data.success) {{'
            '      alert("✓ " + data.message);'
            '      location.reload();'
            '    }} else {{'
            '      alert("✗ " + data.message);'
            '    }}'
            '  }})'
            '  .catch(function(error) {{'
            '    console.error("Error:", error);'
            '    alert("Error: " + error.message);'
            '  }});'
            '}}'
            '</script>'
        )
        
        return format_html('{}{}{}', test_btn, last_test, script)
    connection_test_display.short_description = 'Connection Test'
    
    def test_connection(self, request, queryset):
        """Test Redis connection for selected configs"""
        results = []
        for config in queryset:
            success, message = config.test_connection()
            results.append(f"{config.name}: {message}")
            
        self.message_user(
            request,
            "\n".join(results),
            level='SUCCESS' if all('Success' in r for r in results) else 'WARNING'
        )
    test_connection.short_description = '🔌 Test Redis Connection'
    
    def activate_config(self, request, queryset):
        """Activate selected config (only one can be active)"""
        if queryset.count() != 1:
            self.message_user(
                request,
                'Please select exactly one configuration to activate',
                level='ERROR'
            )
            return
        
        config = queryset.first()
        config.is_active = True
        config.save()
        
        # Reset cache service singleton to reload config
        from ..infrastructure.redis_adapter import reset_cache_service
        reset_cache_service()
        
        self.message_user(
            request,
            f'Configuration "{config.name}" activated. Cache service reloaded.',
            level='SUCCESS'
        )
    activate_config.short_description = '✓ Activate Configuration'
    
    def clear_all_cache(self, request, queryset):
        """Clear all cache entries"""
        from ..infrastructure.redis_adapter import get_cache_service
        from ..domain.cache_service import CacheKeyBuilder
        
        try:
            cache = get_cache_service()
            
            # Clear all crawl service cache patterns
            jobs_cleared = cache.clear_pattern(CacheKeyBuilder.all_jobs_pattern())
            urls_cleared = cache.clear_pattern(CacheKeyBuilder.all_urls_pattern())
            
            self.message_user(
                request,
                f'Cache cleared: {jobs_cleared} job keys, {urls_cleared} URL keys',
                level='SUCCESS'
            )
        except Exception as e:
            self.message_user(
                request,
                f'Failed to clear cache: {str(e)}',
                level='ERROR'
            )
    clear_all_cache.short_description = '🗑️ Clear All Cache'
    
    def disable_cache(self, request, queryset):
        """Disable caching for selected configs"""
        count = queryset.update(enabled=False)
        
        # Reset cache service
        from ..infrastructure.redis_adapter import reset_cache_service
        reset_cache_service()
        
        self.message_user(
            request,
            f'{count} configuration(s) disabled. Cache service reloaded.',
            level='WARNING'
        )
    disable_cache.short_description = '🔴 Disable Cache'


# Register models to CustomAdminSite (hash-protected)
default_admin_site.register(CrawlJob, CrawlJobAdmin)
default_admin_site.register(CrawlResult, CrawlResultAdmin)
default_admin_site.register(BotConfig, BotConfigAdmin)

# Import CrawlCacheConfig and register
from ..models import CrawlCacheConfig
default_admin_site.register(CrawlCacheConfig, CrawlCacheConfigAdmin)
default_admin_site.register(JobResetRule, JobResetRuleAdmin)
