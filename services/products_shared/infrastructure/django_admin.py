"""
Django Admin Configuration for Shared Products Data

Based on PRODUCTS_DATA_CONTRACT.md architecture.
Models in PUBLIC schema: Domain, ProductURL, PriceHistory
"""
from django.contrib import admin
from django import forms
from core.admin_core.infrastructure.custom_admin import default_admin_site
from services.products_shared.infrastructure.django_models import (
    Domain,
    ProductURL,
    PriceHistory,
)
class PriceHistoryInlineForm(forms.ModelForm):
    class Meta:
        model = PriceHistory
        fields = (
            'price', 'currency', 'original_price', 'is_available',
            'stock_status', 'stock_quantity', 'source', 'scraped_at'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            from django.utils import timezone
            self.fields['currency'].initial = 'JPY'
            self.fields['source'].initial = 'MANUAL'
            self.fields['is_available'].initial = True
            self.fields['scraped_at'].initial = timezone.now()
        except Exception:
            pass


class PriceHistoryInline(admin.TabularInline):
    """Inline to add PriceHistory entries on ProductURL change page."""
    model = PriceHistory
    extra = 1
    can_delete = False
    fields = (
        'price', 'currency', 'original_price', 'is_available',
        'stock_status', 'stock_quantity', 'source', 'scraped_at'
    )
    readonly_fields = ()
    form = PriceHistoryInlineForm



@admin.register(Domain, site=default_admin_site)
class DomainAdmin(admin.ModelAdmin):
    """Admin interface for Domain."""
    list_display = ['name', 'get_url_count', 'is_active', 'health_status', 'created_at']
    list_filter = ['is_active', 'health_status']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def get_url_count(self, obj):
        """Count URLs for this domain."""
        return obj.urls.count()
    get_url_count.short_description = 'URL Count'


@admin.register(ProductURL, site=default_admin_site)
class ProductURLAdmin(admin.ModelAdmin):
    """Admin interface for ProductURL."""
    list_display = ['get_domain_name', 'url_hash_short', 'reference_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'domain']
    search_fields = ['raw_url', 'normalized_url', 'url_hash']
    readonly_fields = ['id', 'url_hash', 'normalized_url', 'created_at', 'updated_at']
    inlines = [PriceHistoryInline]

    def save_formset(self, request, form, formset, change):
        """Custom save to avoid writing duplicate consecutive price entries.
        Compares against the most recent PriceHistory for this ProductURL.
        If the new price equals the last recorded price, skip saving and
        notify the user.
        """
        if formset.model is PriceHistory:
            parent = form.instance  # ProductURL
            saved_count = 0
            skipped_count = 0

            # Fetch latest history once
            last = PriceHistory.objects.filter(product_url=parent).order_by('-scraped_at').first()

            # Process each inline form
            for f in formset.forms:
                if not hasattr(f, 'cleaned_data'):
                    continue
                cd = getattr(f, 'cleaned_data', {}) or {}
                if not cd or cd.get('DELETE', False):
                    continue

                new_price = cd.get('price')

                # Compare only price per requirement
                if last is not None and last.price == new_price:
                    skipped_count += 1
                    continue

                obj = f.save(commit=False)
                obj.product_url = parent
                obj.save()
                saved_count += 1
                last = obj  # Update last reference to the newly saved record

            # Handle deletions
            for obj in formset.deleted_objects:
                obj.delete()

            # Feedback messages
            if saved_count:
                from django.contrib import messages
                messages.success(request, f"✓ Added {saved_count} new price history entrie(s)")
            if skipped_count:
                from django.contrib import messages
                messages.warning(request, f"✗ Skipped {skipped_count} duplicate price entrie(s) (no change)")
        else:
            # Default behavior for other formsets
            formset.save()
    
    def get_domain_name(self, obj):
        """Get domain name."""
        return obj.domain.name if obj.domain else ''
    get_domain_name.short_description = 'Domain'
    
    def url_hash_short(self, obj):
        """Display shortened URL hash."""
        return obj.url_hash[:16] + '...' if obj.url_hash else ''
    url_hash_short.short_description = 'URL Hash'


@admin.register(PriceHistory, site=default_admin_site)
class PriceHistoryAdmin(admin.ModelAdmin):
    """Admin interface for PriceHistory."""
    list_display = [
        'get_domain_name',
        'get_product_url',
        'price',
        'currency',
        'is_available',
        'source',
        'scraped_at',
    ]
    list_filter = ['currency', 'source', 'is_available', 'product_url__domain']
    search_fields = ['url_hash', 'product_url__raw_url', 'product_url__domain__name']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'scraped_at'
    list_select_related = ('product_url', 'product_url__domain')
    raw_id_fields = ['product_url']
    
    def get_domain_name(self, obj):
        """Display domain of the product URL."""
        return obj.product_url.domain.name if obj.product_url and obj.product_url.domain else ''
    get_domain_name.short_description = 'Domain'

    def get_product_url(self, obj):
        """Display a shortened product URL for quick inspection."""
        if not obj.product_url:
            return ''
        raw = obj.product_url.raw_url or ''
        return (raw[:80] + '...') if len(raw) > 80 else raw
    get_product_url.short_description = 'Product URL'


# Register custom admin view for ProductURL Price Dashboard
def register_product_url_price_dashboard(admin_site):
    """Register custom view for ProductURL with latest prices and history."""
    from django.urls import path
    from django.shortcuts import get_object_or_404
    from django.http import JsonResponse
    from django.views.decorators.http import require_http_methods
    from django.db.models import Count, Q
    
    class ProductURLPriceDashboard:
        """Dashboard view for ProductURL with price tracking and history."""
        
        def __init__(self, admin_site):
            self.admin_site = admin_site
        
        def list_view(self, request):
            """List all ProductURLs with latest price, price status, and trend."""
            from django.template.response import TemplateResponse
            
            urls = ProductURL.objects.select_related('domain').prefetch_related('price_history').all()
            
            # Apply search from request
            search_query = request.GET.get('q', '').strip()
            
            # Apply filters from request
            domain_filter = request.GET.get('domain', '')
            source_filter = request.GET.get('source', '')
            availability_filter = request.GET.get('availability', '')
            currency_filter = request.GET.get('currency', '')
            
            # Collect available filter values
            domains = ProductURL.objects.values_list('domain__name', flat=True).distinct().order_by('domain__name')
            sources = PriceHistory.objects.values_list('source', flat=True).distinct().order_by('source')
            currencies = PriceHistory.objects.values_list('currency', flat=True).distinct().order_by('currency')
            
            # Enrich with price data and apply filters
            urls_with_prices = []
            for url_obj in urls:
                latest = url_obj.price_history.order_by('-scraped_at').first()
                if not latest:
                    continue
                
                # Apply search filter
                if search_query:
                    if search_query.lower() not in url_obj.normalized_url.lower() and \
                       search_query.lower() not in (url_obj.domain.name or '').lower():
                        continue
                
                # Apply filters
                if domain_filter and url_obj.domain.name != domain_filter:
                    continue
                if source_filter and latest.source != source_filter:
                    continue
                if availability_filter and str(latest.is_available) != availability_filter:
                    continue
                if currency_filter and latest.currency != currency_filter:
                    continue
                
                previous = url_obj.price_history.order_by('-scraped_at')[1] if url_obj.price_history.count() > 1 else None
                
                # Determine price trend and change
                change_amount = 0
                trend = '➡️ No change'
                
                if previous and float(previous.price) != float(latest.price):
                    change_amount = float(latest.price) - float(previous.price)
                    if change_amount > 0:
                        trend = '📈 Increase'
                    else:
                        trend = '📉 Decrease'
                
                urls_with_prices.append({
                    'id': url_obj.id,
                    'url_hash': url_obj.url_hash,
                    'domain': url_obj.domain.name if url_obj.domain else 'N/A',
                    'url': url_obj.normalized_url,
                    'url_short': (url_obj.normalized_url[:80] + '...') if len(url_obj.normalized_url) > 80 else url_obj.normalized_url,
                    'latest_price': float(latest.price),
                    'latest_currency': latest.currency,
                    'previous_price': float(previous.price) if previous else None,
                    'trend': trend,
                    'change_amount': change_amount,
                    'updated_at': latest.scraped_at,
                    'source': latest.source,
                    'is_available': latest.is_available,
                    'history_count': url_obj.price_history.count(),
                })
            
            # Get admin site context
            extra_context = self.admin_site.each_context(request)
            
            extra_context.update({
                'title': 'Product URL Price Dashboard',
                'has_filters': True,
                'result_list': urls_with_prices,
                'result_count': len(urls_with_prices),
                'total_urls': len(urls_with_prices),
                # Filter values for sidebar
                'domains': [(d, d) for d in domains if d],
                'sources': [(s, s) for s in sources if s],
                'currencies': [(c, c) for c in currencies if c],
                'availability_choices': [('True', 'In Stock'), ('False', 'Out of Stock')],
                # Currently selected filters
                'selected_domain': domain_filter,
                'selected_source': source_filter,
                'selected_availability': availability_filter,
                'selected_currency': currency_filter,
                # Search query
                'search_query': search_query,
            })
            
            return TemplateResponse(request, 'admin/products_shared_price_dashboard.html', extra_context)
        
        def detail_view(self, request, url_hash):
            """Display detailed price history for a specific ProductURL."""
            from django.template.response import TemplateResponse
            from django.shortcuts import get_object_or_404
            
            url_obj = get_object_or_404(ProductURL, url_hash=url_hash)
            
            # Get all price histories
            histories = list(url_obj.price_history.order_by('-scraped_at'))
            
            # Calculate statistics
            price_stats = {
                'total_records': len(histories),
                'highest': max([float(h.price) for h in histories]) if histories else 0,
                'lowest': min([float(h.price) for h in histories]) if histories else 0,
                'avg': sum([float(h.price) for h in histories]) / len(histories) if histories else 0,
            }
            
            # Enrich with trend data
            histories_list = []
            for i, history in enumerate(histories):
                change_amount = None
                change_indicator = None
                
                if i < len(histories) - 1:  # Not the last (oldest) record
                    prev_history = histories[i + 1]
                    if float(history.price) != float(prev_history.price):
                        change_amount = float(history.price) - float(prev_history.price)
                        if change_amount > 0:
                            change_indicator = f'📈 +{change_amount:,.0f}'
                        else:
                            change_indicator = f'📉 {change_amount:,.0f}'
                    else:
                        change_amount = 0
                        change_indicator = '➡️ 0'
                else:
                    # First time recording
                    change_amount = None
                    change_indicator = None
                
                histories_list.append({
                    'recorded_at': history.scraped_at,
                    'price': history.price,
                    'currency': history.currency,
                    'original_price': history.original_price,
                    'is_available': history.is_available,
                    'stock_status': history.stock_status,
                    'stock_quantity': history.stock_quantity,
                    'source': history.source,
                    'change_amount': change_amount,
                    'change_indicator': change_indicator,
                })
            
            # Get latest price info
            latest = histories[0] if histories else None
            url_data = {
                'domain': url_obj.domain.name if url_obj.domain else 'N/A',
                'url': url_obj.normalized_url,
                'url_hash': url_obj.url_hash,
                'latest_price': float(latest.price) if latest else 0,
                'latest_currency': latest.currency if latest else 'VND',
                'updated_at': latest.scraped_at if latest else None,
                'source': latest.source if latest else 'N/A',
                'is_available': latest.is_available if latest else False,
                'price_stats': price_stats,
                'history': histories_list,
            }
            
            # Get admin site context
            extra_context = self.admin_site.each_context(request)
            
            extra_context.update({
                'title': f'💰 Price History - {url_obj.normalized_url[:80]}',
                'url_data': url_data,
            })
            
            return TemplateResponse(request, 'admin/products_shared_price_history_detail.html', extra_context)
    
    # Create view instance
    dashboard = ProductURLPriceDashboard(admin_site)
    
    # Return URL patterns for admin site
    return [
        path('products_shared/producturl/price-dashboard/', dashboard.list_view, name='products_shared_price_dashboard'),
        path('products_shared/producturl/price-history/<str:url_hash>/', dashboard.detail_view, name='products_shared_price_history_detail'),
    ]
