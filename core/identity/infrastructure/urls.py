"""URL configuration for Identity module."""
from django.urls import path
from core.identity.api import views as api_views

app_name = 'identity_api'

urlpatterns = [
    # Authentication endpoints
    path('signup/', api_views.signup_view, name='signup'),
    path('login/', api_views.login_view, name='login'),
    path('logout/', api_views.logout_view, name='logout'),
    path('check-auth/', api_views.check_auth_view, name='check_auth'),
    path('change-password/', api_views.change_password_view, name='change_password'),
    
    # Email verification endpoints
    path('request-email-verification/', api_views.request_email_verification_view, name='request_email_verification'),
    path('verify-email/', api_views.verify_email_view, name='verify_email'),
    
    # Password reset endpoints
    path('request-password-reset/', api_views.request_password_reset_view, name='request_password_reset'),
    path('reset-password/', api_views.reset_password_view, name='reset_password'),
    
    # Magic link login endpoints
    path('request-magic-link/', api_views.request_magic_link_view, name='request_magic_link'),
    path('magic-login/', api_views.magic_link_login_view, name='magic_login'),
]
