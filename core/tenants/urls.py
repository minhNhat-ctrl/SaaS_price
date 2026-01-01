"""
URL Configuration cho Tenant API endpoints
"""
from django.urls import path
from core.tenants.infrastructure import api_views

app_name = 'tenants'

urlpatterns = [
    # List and create (combined view will handle both GET and POST)
    path('', api_views.tenants_list_create_view, name='list_create'),
    
    # Get, update, delete (combined view will handle GET, PATCH, DELETE)
    path('<uuid:tenant_id>/', api_views.tenant_detail_view, name='detail'),
    
    # Actions
    path('<uuid:tenant_id>/activate/', api_views.activate_tenant_view, name='activate'),
    path('<uuid:tenant_id>/suspend/', api_views.suspend_tenant_view, name='suspend'),
    path('<uuid:tenant_id>/add-domain/', api_views.add_domain_view, name='add_domain'),
]
