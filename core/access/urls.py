"""URL configuration for Access module."""
from django.urls import path
from core.access.infrastructure import api_views

app_name = 'access'

urlpatterns = [
    # Membership management
    path('memberships/', api_views.list_memberships_view, name='list_memberships'),
    path('memberships/invite/', api_views.invite_member_view, name='invite_member'),
    path('memberships/<uuid:membership_id>/activate/', api_views.activate_membership_view, name='activate_membership'),
    path('memberships/<uuid:membership_id>/revoke/', api_views.revoke_membership_view, name='revoke_membership'),
    path('memberships/<uuid:membership_id>/assign-roles/', api_views.assign_roles_view, name='assign_roles'),
    
    # Role management
    path('roles/', api_views.list_roles_view, name='list_roles'),
    path('roles/create/', api_views.create_custom_role_view, name='create_role'),
    
    # Permission checking
    path('check-permission/', api_views.check_permission_view, name='check_permission'),
]
