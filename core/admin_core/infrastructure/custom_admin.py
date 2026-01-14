"""
Custom Admin Site - Auto-load modules, auto-register models

Custom AdminSite có thể:
1. Gọi AdminService để load modules
2. Gọi AdminService để lấy stats
3. Customize branding
4. Add custom views
5. Provide logging & monitoring

Nguyên tắc:
- Gọi AdminService (không gọi loader/hash service trực tiếp)
- AdminService điều phối tất cả logic
- Infrastructure chỉ handle presentation
"""
from django.contrib import admin
from django.apps import apps
import logging

logger = logging.getLogger(__name__)


class CustomAdminSite(admin.AdminSite):
    """
    Custom AdminSite cho platform
    
    Features:
    - Gọi AdminService để load modules
    - Gọi AdminService để lấy stats
    - Custom branding
    - Security logging
    
    Dependencies:
    - AdminService (injected by app ready)
    """

    site_header = "PriceSynC - Admin Dashboard"
    site_title = "Platform Admin"
    index_title = "System Administration"

    def __init__(self, name='admin'):
        super().__init__(name)
        # AdminService sẽ được inject ở ready()
        self.admin_service = None

    def set_admin_service(self, service):
        """Set AdminService instance (called by app ready)"""
        self.admin_service = service

    def each_context(self, request):
        """
        Add custom context cho admin template
        """
        context = super().each_context(request)
        
        if not self.admin_service:
            logger.warning("AdminService not initialized in CustomAdminSite")
            return context
        
        try:
            # Gọi AdminService (không gọi loader trực tiếp)
            import asyncio
            
            loaded_modules = asyncio.run(self.admin_service.get_loaded_modules())
            failed_modules = asyncio.run(self.admin_service.get_failed_modules())
            
            context['loaded_modules'] = len(loaded_modules)
            context['failed_modules'] = len(failed_modules)
            context['admin_url'] = self.admin_service.get_admin_url()
            
            # Security info
            client_ip = self._get_client_ip(request)
            context['failed_attempts'] = self.admin_service.get_failed_attempts_for_ip(client_ip)
            context['max_failed_attempts'] = self.admin_service.max_failed_attempts
            
        except Exception as e:
            logger.error(f"Error getting admin stats: {str(e)}")

        return context

    def get_urls(self):
        """Override để thêm custom URLs"""
        from django.urls import path
        
        urls = super().get_urls()
        
        # Custom views - wrap with admin_view for permission checks
        custom_urls = [
            path('modules/', self.admin_view(self.modules_view), name='admin_modules'),
            path('stats/', self.admin_view(self.stats_view), name='admin_stats'),
            # Crawl Service auto-record config
            path('crawl_service/auto-record-config/', self.admin_view(self.auto_record_config_view), name='admin_crawl_auto_record_config'),
            # Crawl Service JobResetRule scheduler management (different path to avoid conflict)
            path('crawl_service/jobresetrule-scheduler/', self.admin_view(self.job_reset_rule_scheduler_view), name='admin_crawl_job_reset_rule_scheduler'),
        ]
        
        # Add ProductURL Price Dashboard URLs (from products_shared module)
        try:
            from services.products_shared.infrastructure.django_admin import register_product_url_price_dashboard
            product_urls = register_product_url_price_dashboard(self)
            custom_urls.extend([
                path(f'{url.pattern._route}/', self.admin_view(url.callback), name=url.name) 
                for url in product_urls
            ])
        except Exception as e:
            logger.warning(f"Could not register ProductURL Price Dashboard: {e}")
        
        return custom_urls + urls

    def modules_view(self, request):
        """View hiển thị danh sách modules"""
        from django.shortcuts import render
        
        modules = []
        failed = {}
        
        if self.admin_service:
            try:
                import asyncio
                modules = asyncio.run(self.admin_service.get_loaded_modules())
                failed = asyncio.run(self.admin_service.get_failed_modules())
            except Exception as e:
                logger.error(f"Error loading modules view: {str(e)}")

        context = {
            **self.each_context(request),
            'modules': modules,
            'failed_modules': failed,
        }
        return render(request, 'admin/modules.html', context)

    def stats_view(self, request):
        """View hiển thị stats"""
        from django.shortcuts import render
        
        stats = {
            'total_apps': len(list(apps.get_app_configs())),
            'total_models': len(apps.get_models()),
        }

        if self.admin_service:
            try:
                import asyncio
                loaded = asyncio.run(self.admin_service.get_loaded_modules())
                failed = asyncio.run(self.admin_service.get_failed_modules())
                stats['loaded_modules'] = len(loaded)
                stats['failed_modules'] = len(failed)
            except Exception as e:
                logger.error(f"Error loading stats view: {str(e)}")

        context = {
            **self.each_context(request),
            'stats': stats,
        }
        return render(request, 'admin/stats.html', context)

    def crawl_create_jobs_view(self, request):
                """Admin view to trigger job import from shared products

                Displays a simple form (GET submission) to avoid manual query params.
                """
                from django.shortcuts import redirect
                from django.contrib import messages
                from django.http import HttpResponse
                from services.crawl_service.utils import create_jobs_from_shared
                from services.products_shared.infrastructure.django_models import Domain

                # Form submission via GET to avoid CSRF template setup here
                rule_id = request.GET.get('rule')
                domain = request.GET.get('domain')
                limit = request.GET.get('limit')
                only_active = request.GET.get('only_active')

                # If no rule specified, render a simple form
                if not rule_id:
                        # rules = ScheduleRule.objects.order_by('name')  # ScheduleRule removed
                        domains = Domain.objects.order_by('name')
                        # Build options
                        # rule_options = "".join([f'<option value="{r.id}">{r.name}</option>' for r in rules])
                        domain_options = '<option value="">-- Any Domain --</option>' + "".join([
                                f'<option value="{d.name}">{d.name}</option>' for d in domains
                        ])

                        html = f"""
                        <div class="module">
                            <h2>Create Crawl Jobs from Shared Products</h2>
                            <p style="color: red; font-weight: bold;">This feature is temporarily disabled (ScheduleRule model removed).</p>
                            <p>Please use CrawlJob admin to manage jobs directly.</p>
                        </div>
                        """
                        return HttpResponse(html)

                # Normalize only_active flag
                only_active_flag = True
                if only_active is not None:
                        only_active_flag = str(only_active).lower() not in ('false', '0', 'no')

                try:
                        created = create_jobs_from_shared(
                                schedule_rule_id=rule_id,
                                domain_name=domain or None,
                                limit=int(limit) if limit else None,
                                only_active=only_active_flag,
                        )
                        msg = f'Imported {created} jobs from shared products'
                        if domain:
                                msg += f' (domain={domain})'
                        if limit:
                                msg += f' (limit={limit})'
                        messages.success(request, msg)
                except Exception as e:
                        messages.error(request, f'Error importing jobs: {str(e)}')

                # Redirect back to Crawl Jobs list
                return redirect('../crawl_service/crawljob/')

    def auto_record_config_view(self, request):
        """
        Render and manage auto-record configuration for crawl results.
        
        Includes scheduler management (start/stop/status).
        
        GET: Display current config in form
        POST: Save updated config OR control scheduler (start/stop)
        
        NOTE: Only processes POST if explicit action is provided from form submission.
        Prevents unintended triggers on page refresh/reload.
        """
        from django.shortcuts import render, redirect
        from django.contrib import messages
        from services.crawl_service.infrastructure.auto_recording import (
            get_auto_record_config,
            save_auto_record_config,
        )
        from services.crawl_service.infrastructure.scheduler_manager import get_scheduler_manager
        
        scheduler_manager = get_scheduler_manager()
        
        if request.method == 'POST' and request.POST.get('action'):
            action = request.POST.get('action')
            
            # Handle scheduler control actions
            if action == 'start_scheduler':
                success, msg = scheduler_manager.start()
                if success:
                    messages.success(request, f'✓ {msg}')
                else:
                    messages.error(request, f'✗ {msg}')
                cfg = get_auto_record_config()
            
            elif action == 'stop_scheduler':
                success, msg = scheduler_manager.stop()
                if success:
                    messages.success(request, f'✓ {msg}')
                else:
                    messages.error(request, f'✗ {msg}')
                cfg = get_auto_record_config()
            
            elif action == 'reload_config':
                scheduler_manager.reload_config()
                messages.success(request, '✓ Scheduler configuration reloaded from file')
                cfg = get_auto_record_config()
            
            # Handle config save
            elif action == 'save_config':
                # Parse form submission
                enabled = request.POST.get('enabled') == 'on'
                allowed_sources = [s.strip() for s in (request.POST.get('allowed_sources') or '').split(',') if s.strip()]
                min_confidence_str = request.POST.get('min_confidence', '0.85')
                require_in_stock = request.POST.get('require_in_stock') == 'on'
                allowed_domains = [d.strip() for d in (request.POST.get('allowed_domains') or '').split(',') if d.strip()]
                currency_whitelist = [c.strip().upper() for c in (request.POST.get('currency_whitelist') or '').split(',') if c.strip()]
                
                # Parse cron config
                scheduler_enabled = request.POST.get('scheduler_enabled') == 'on'
                try:
                    interval_seconds = int(request.POST.get('interval_seconds', '30'))
                    batch_size = int(request.POST.get('batch_size', '100'))
                    max_retries = int(request.POST.get('max_retries', '3'))
                except (ValueError, TypeError):
                    interval_seconds = 30
                    batch_size = 100
                    max_retries = 3
                
                # Parse confidence as float
                try:
                    min_confidence = float(min_confidence_str) if min_confidence_str else 0.85
                    min_confidence = max(0.0, min(1.0, min_confidence))  # clamp 0-1
                except (ValueError, TypeError):
                    min_confidence = 0.85
                
                # Build config - IMPORTANT: preserve _cron_config structure
                config_data = {
                    'enabled': enabled,
                    'allowed_sources': allowed_sources or ['jsonld', 'og', 'microdata', 'script_data', 'html_ml'],
                    'min_confidence': min_confidence,
                    'require_in_stock': require_in_stock,
                    'allowed_domains': allowed_domains,
                    'currency_whitelist': currency_whitelist,
                    '_cron_config': {
                        '_comment': 'Cron configuration for auto-record scheduler',
                        'scheduler_enabled': scheduler_enabled,
                        'interval_seconds': interval_seconds,
                        'batch_size': batch_size,
                        'max_retries': max_retries,
                        'retry_failed_every_n_cycles': 50,
                        'retry_failed_limit': 20,
                        'log_queue_status_every_n_cycles': 10,
                    }
                }
                
                try:
                    save_auto_record_config(config_data)
                    messages.success(request, f'✓ Configuration saved: scheduler_enabled={scheduler_enabled}, interval={interval_seconds}s, batch={batch_size}')
                    # Reload scheduler config if running
                    if scheduler_manager.is_running():
                        scheduler_manager.reload_config()
                        messages.info(request, 'ℹ️ Scheduler config reloaded (will take effect on next cycle)')
                    cfg = get_auto_record_config()
                except Exception as e:
                    messages.error(request, f'✗ Failed to save config: {str(e)}')
                    cfg = get_auto_record_config()
        else:
            # GET: Display current config
            cfg = get_auto_record_config()
        
        # Get scheduler status
        scheduler_status = scheduler_manager.get_status()
        
        # Extract cron_config to avoid underscore in template
        # Provide defaults if _cron_config doesn't exist
        cron_config = cfg.get('_cron_config', {
            'scheduler_enabled': True,
            'interval_seconds': 30,
            'batch_size': 100,
            'max_retries': 3,
        })
        
        context = {
            **self.each_context(request),
            'title': 'Auto-Record Configuration & Scheduler',
            'cfg': cfg,
            'cron_config': cron_config,
            'all_sources': ['jsonld', 'og', 'microdata', 'script_data', 'html_ml'],
            'scheduler_status': scheduler_status,
        }
        
        return render(request, 'admin/crawl_auto_record_config.html', context)

    def job_reset_rule_scheduler_view(self, request):
        """
        Render and manage JobResetRule scheduler.
        
        GET: Display current status and rules
        POST: Control scheduler (start/stop)
        
        NOTE: Only processes POST if explicit action is provided from form submission.
        Prevents unintended triggers on page refresh/reload.
        """
        from django.shortcuts import render
        from django.contrib import messages
        from services.crawl_service.models import JobResetRule
        from services.crawl_service.infrastructure.job_reset_rule_scheduler import get_job_reset_rule_scheduler
        
        scheduler = get_job_reset_rule_scheduler()
        
        if request.method == 'POST' and request.POST.get('action'):
            action = request.POST.get('action')
            
            if action == 'start_scheduler':
                success, msg = scheduler.start()
                if success:
                    messages.success(request, f'✓ {msg}')
                else:
                    messages.error(request, f'✗ {msg}')
            
            elif action == 'stop_scheduler':
                success, msg = scheduler.stop()
                if success:
                    messages.success(request, f'✓ {msg}')
                else:
                    messages.error(request, f'✗ {msg}')
            
            elif action == 'run_now':
                try:
                    scheduler.run_resets()
                    messages.success(request, '✓ JobResetRule resets executed')
                except Exception as e:
                    messages.error(request, f'✗ Error running resets: {str(e)}')
        
        # Get all rules
        rules = JobResetRule.objects.all().order_by('-enabled', 'name')
        
        # Calculate next execution for each rule
        for rule in rules:
            rule_id = str(rule.id)
            last_exec = scheduler.rule_last_execution.get(rule_id)
            if last_exec:
                from datetime import timedelta
                next_exec = last_exec + timedelta(hours=rule.frequency_hours)
                rule.next_execution = next_exec
                rule.last_execution = last_exec
            else:
                rule.next_execution = None
                rule.last_execution = None
        
        context = {
            **self.each_context(request),
            'title': 'JobResetRule Scheduler Management',
            'scheduler_running': scheduler.is_running(),
            'scheduler_stats': scheduler.stats,
            'rules': rules,
        }
        
        return render(request, 'admin/crawl_job_reset_rule_scheduler.html', context)

    @staticmethod
    def _get_client_ip(request) -> str:
        """Extract client IP từ request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


# Create default admin site instance
default_admin_site = CustomAdminSite()
