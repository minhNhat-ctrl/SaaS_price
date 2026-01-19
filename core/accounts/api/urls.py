"""URL configuration for Accounts API views."""
from django.urls import path

from core.accounts.api import views

app_name = "accounts_api"

urlpatterns = [
    path("profile/", views.get_profile_view, name="profile"),
    path("profile/update/", views.update_profile_view, name="profile_update"),
    path("preferences/", views.get_preferences_view, name="preferences"),
    path("preferences/update/", views.update_preferences_view, name="preferences_update"),
    path("notification-settings/", views.get_notification_settings_view, name="notification_settings"),
    path("notification-settings/update/", views.update_notification_settings_view, name="notification_settings_update"),
    path("avatar/", views.get_avatar_view, name="avatar"),
    path("avatar/upload/", views.upload_avatar_view, name="avatar_upload"),
    path("avatar/remove/", views.remove_avatar_view, name="avatar_remove"),
]
