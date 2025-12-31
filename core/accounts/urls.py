"""URL configuration for Accounts module."""
from django.urls import path
from core.accounts.infrastructure import api_views

app_name = 'accounts_api'

urlpatterns = [
    # Profile management endpoints
    path('profile/', api_views.get_profile_view, name='profile_get'),
    path('profile/update/', api_views.update_profile_view, name='profile_update'),
    
    # Preferences endpoints
    path('preferences/', api_views.get_preferences_view, name='preferences_get'),
    path('preferences/update/', api_views.update_preferences_view, name='preferences_update'),
]
