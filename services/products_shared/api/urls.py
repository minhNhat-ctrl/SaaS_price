"""
URL Configuration for Products Shared Module API

Routes (Shared - Public Schema):
- GET /api/price-history/
  Query params: ?url_hash=<hash>&limit=100
  Returns: Price history for specific URL

- POST /api/price-history/
  Body: {url_hash, price, currency, ...}
  Records: New price entry for URL

- GET /api/product-urls/
  Query params: ?domain=example.com
  Returns: All ProductURLs in shared catalog (read-only)

- POST /api/product-urls/
  Body: {raw_url, domain}
  Registers: New ProductURL in shared catalog (read-only after)

Note: These are SHARED module endpoints (public schema)
      Tenant product→URL mapping is in Products module
"""

from django.urls import path
from .views import ProductPriceHistoryView, ProductURLView

urlpatterns = [
    # Price history endpoints - URL-scoped, NOT product-scoped
    path('price-history/', ProductPriceHistoryView.as_view(), name='price-history'),
    
    # Product URL endpoints - read-only shared catalog
    path('product-urls/', ProductURLView.as_view(), name='product-urls'),
]
