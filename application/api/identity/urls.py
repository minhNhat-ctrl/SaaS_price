"""Identity API URLs."""
from django.urls import path

from .signup import SignupView
from .signin import SigninView
from .recover_password import RecoverPasswordView
from .verify_email import VerifyEmailView
from .password_reset_confirm import PasswordResetConfirmView


urlpatterns = [
    path("signup/", SignupView.as_view(), name="identity-signup"),
    path("signin/", SigninView.as_view(), name="identity-signin"),
    path("verify-email/", VerifyEmailView.as_view(), name="identity-verify-email"),
    # Match frontend path: /api/identity/password-recovery/
    path("password-recovery/", RecoverPasswordView.as_view(), name="identity-password-recovery"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="identity-password-reset-confirm"),
]
