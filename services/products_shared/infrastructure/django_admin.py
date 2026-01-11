"""
Django Admin Configuration for Shared Products Data

Based on PRODUCTS_DATA_CONTRACT.md architecture.
Models in PUBLIC schema: Domain, ProductURL, PriceHistory
"""
from django.contrib import admin
from django import forms
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



@admin.register(Domain)
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


@admin.register(ProductURL)
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


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    """Admin interface for PriceHistory."""
    list_display = ['url_hash_short', 'price', 'currency', 'is_available', 'source', 'scraped_at']
    list_filter = ['currency', 'source', 'is_available']
    search_fields = ['url_hash']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'scraped_at'
    
    def url_hash_short(self, obj):
        """Display shortened URL hash."""
        return obj.url_hash[:16] + '...' if obj.url_hash else ''
    url_hash_short.short_description = 'URL Hash'
