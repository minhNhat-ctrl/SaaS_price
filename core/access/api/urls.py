"""URL patterns for Access API views."""
from django.urls import path

from core.access.api import views

app_name = "access"

urlpatterns = [
    path("memberships/", views.list_memberships_view, name="list_memberships"),
    path("memberships/invite/", views.invite_member_view, name="invite_member"),
    path("memberships/<uuid:membership_id>/activate/", views.activate_membership_view, name="activate_membership"),
    path("memberships/<uuid:membership_id>/revoke/", views.revoke_membership_view, name="revoke_membership"),
    path("memberships/<uuid:membership_id>/assign-roles/", views.assign_roles_view, name="assign_roles"),
    path("roles/", views.list_roles_view, name="list_roles"),
    path("roles/create/", views.create_custom_role_view, name="create_role"),
    path("check-permission/", views.check_permission_view, name="check_permission"),
]
