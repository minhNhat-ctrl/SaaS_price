"""
URL Configuration for Products Shared Module API

Routes:
- GET /api/products/{product_id}/prices/
- POST /api/products/{product_id}/prices/
- GET /api/products/{product_id}/urls/
- POST /api/products/{product_id}/urls/
- DELETE /api/products/{product_id}/urls/{url_hash}/
"""

from django.urls import path
from .views import ProductPriceHistoryView, ProductURLView

urlpatterns = [
    # Price history endpoints
    path('products/<str:product_id>/prices/', ProductPriceHistoryView.as_view(), name='product-prices'),
    
    # Product URL endpoints
    path('products/<str:product_id>/urls/', ProductURLView.as_view(), name='product-urls'),
]
