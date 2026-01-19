"""URL configuration for Identity HTTP adapters."""
from django.urls import path

from core.identity.api import views

app_name = "identity_api"

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("check-auth/", views.check_auth_view, name="check_auth"),
    path("change-password/", views.change_password_view, name="change_password"),
    path("request-email-verification/", views.request_email_verification_view, name="request_email_verification"),
    path("verify-email/", views.verify_email_view, name="verify_email"),
    path("request-password-reset/", views.request_password_reset_view, name="request_password_reset"),
    path("reset-password/", views.reset_password_view, name="reset_password"),
    path("request-magic-link/", views.request_magic_link_view, name="request_magic_link"),
    path("magic-login/", views.magic_link_login_view, name="magic_login"),
]
