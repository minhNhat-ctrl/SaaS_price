"""URL configuration for Identity module."""
from django.urls import path
from . import api_views

app_name = 'identity_api'

urlpatterns = [
    # Authentication endpoints
    path('signup/', api_views.signup_view, name='signup'),
    path('login/', api_views.login_view, name='login'),
    path('logout/', api_views.logout_view, name='logout'),
    path('check-auth/', api_views.check_auth_view, name='check_auth'),
    path('change-password/', api_views.change_password_view, name='change_password'),
]
