"""
API URL Configuration

Based on PRODUCTS_DATA_CONTRACT.md architecture.

Supports two patterns:
1. With tenant_id in URL: /api/products/tenants/<tenant_id>/products/
2. With tenant_id in query params: /api/products/?tenant_id=<uuid>

URL deletion uses url_hash instead of url_id for cross-schema safety.
"""
from django.urls import path

from services.products.api.views import (
    ProductListCreateView,
    ProductDetailView,
    ProductURLsView,
    ProductURLDetailView,
    ProductSearchView,
    PriceHistoryView,
)

app_name = 'products'

urlpatterns = [
    # ============================================================
    # Pattern 1: Tenant-scoped routes (recommended)
    # ============================================================
    path('tenants/<uuid:tenant_id>/products/', ProductListCreateView.as_view(), name='tenant-product-list-create'),
    path('tenants/<uuid:tenant_id>/products/search/', ProductSearchView.as_view(), name='tenant-product-search'),
    path('tenants/<uuid:tenant_id>/products/<uuid:product_id>/', ProductDetailView.as_view(), name='tenant-product-detail'),
    path('tenants/<uuid:tenant_id>/products/<uuid:product_id>/urls/', ProductURLsView.as_view(), name='tenant-product-urls'),
    # url_hash is a SHA-256 hash string (64 chars), not UUID
    path('tenants/<uuid:tenant_id>/products/<uuid:product_id>/urls/<str:url_hash>/', ProductURLDetailView.as_view(), name='tenant-product-url-detail'),
    
    # ============================================================
    # Pattern 2: Query-param tenant routes (for middleware-based tenant)
    # ============================================================
    path('', ProductListCreateView.as_view(), name='product-list-create'),
    path('search/', ProductSearchView.as_view(), name='product-search'),
    path('<uuid:product_id>/', ProductDetailView.as_view(), name='product-detail'),
    path('<uuid:product_id>/urls/', ProductURLsView.as_view(), name='product-urls'),
    # url_hash is a SHA-256 hash string (64 chars), not UUID
    path('<uuid:product_id>/urls/<str:url_hash>/', ProductURLDetailView.as_view(), name='product-url-detail'),
    
    # ============================================================
    # Shared routes (no tenant context needed)
    # url_hash used to identify URLs across schemas
    # ============================================================
    path('urls/<str:url_hash>/price-history/', PriceHistoryView.as_view(), name='price-history'),
]
