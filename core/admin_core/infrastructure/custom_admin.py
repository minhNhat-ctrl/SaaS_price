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
            # Crawl Service dashboard shortcuts
            path('crawl/', self.admin_view(self.crawl_dashboard_view), name='admin_crawl_dashboard'),
            path('crawl/create-jobs/', self.admin_view(self.crawl_create_jobs_view), name='admin_crawl_create_jobs'),
        ]
        
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
            'total_apps': len(apps.get_app_configs()),
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

    def crawl_dashboard_view(self, request):
        """Simple Crawl Service dashboard with shortcuts to models and actions"""
        from django.http import HttpResponse
        base = self.each_context(request)
        # Build shortcut links (respect current admin base path)
        # The admin base includes hash, so relative paths work
        html = f"""
        <div class="module">
          <h2>Crawl Service</h2>
          <ul>
            <li><a href="../crawl_service/schedulerule/">Schedule Rules</a></li>
            <li><a href="../crawl_service/crawljob/">Crawl Jobs</a></li>
            <li><a href="../crawl_service/crawltask/">Crawl Tasks</a></li>
            <li><a href="../crawl_service/crawlresult/">Crawl Results</a></li>
            <li><a href="./create-jobs/">Create Jobs from Shared Products</a></li>
          </ul>
        </div>
        """
        return HttpResponse(html)

    def crawl_create_jobs_view(self, request):
                """Admin view to trigger job import from shared products

                Displays a simple form (GET submission) to avoid manual query params.
                """
                from django.shortcuts import redirect
                from django.contrib import messages
                from django.http import HttpResponse
                from services.crawl_service.utils import create_jobs_from_shared
                from services.crawl_service.models import ScheduleRule
                from services.products_shared.infrastructure.django_models import Domain

                # Form submission via GET to avoid CSRF template setup here
                rule_id = request.GET.get('rule')
                domain = request.GET.get('domain')
                limit = request.GET.get('limit')
                only_active = request.GET.get('only_active')

                # If no rule specified, render a simple form
                if not rule_id:
                        rules = ScheduleRule.objects.order_by('name')
                        domains = Domain.objects.order_by('name')
                        # Build options
                        rule_options = "".join([f'<option value="{r.id}">{r.name}</option>' for r in rules])
                        domain_options = '<option value="">-- Any Domain --</option>' + "".join([
                                f'<option value="{d.name}">{d.name}</option>' for d in domains
                        ])

                        html = f"""
                        <div class="module">
                            <h2>Create Crawl Jobs from Shared Products</h2>
                            <form method="get" action="">
                                <div class="form-row">
                                    <label>Schedule Rule*</label>
                                    <select name="rule" required>
                                        {rule_options}
                                    </select>
                                </div>
                                <div class="form-row">
                                    <label>Domain</label>
                                    <select name="domain">
                                        {domain_options}
                                    </select>
                                </div>
                                <div class="form-row">
                                    <label>Limit</label>
                                    <input type="number" name="limit" min="1" placeholder="e.g. 100" />
                                </div>
                                <div class="form-row">
                                    <label>Only Active URLs</label>
                                    <input type="checkbox" name="only_active" value="true" checked />
                                </div>
                                <div class="submit-row">
                                    <button type="submit" class="default">Create Jobs</button>
                                </div>
                            </form>
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

    @staticmethod
    def _get_client_ip(request) -> str:
        """Extract client IP từ request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


# Create default admin site instance
default_admin_site = CustomAdminSite()
