"""
Products API URLs
"""
from django.urls import path
from services.products.api import views

app_name = 'products'

urlpatterns = [
    # Tenant Products (GET list, POST create)
    path('tenants/<str:tenant_id>/products/', views.products_list_create_view, name='products-list-create'),
    # Tenant Products (GET detail, PATCH update, DELETE)
    path('tenants/<str:tenant_id>/products/<str:product_id>/', views.products_detail_view, name='products-detail'),
    
    # Product URLs (GET list, POST add)
    path('tenants/<str:tenant_id>/products/<str:product_id>/urls/', views.product_urls_view, name='product-urls'),
    
    # Price History (GET history, POST record)
    path('tenants/<str:tenant_id>/products/<str:product_id>/urls/<str:url_id>/prices/', 
         views.price_history_view, name='price-history'),
]
