"""Identity API URLs."""
from django.urls import path

from .signup import SignupView
from .signin import SigninView
from .recover_password import RecoverPasswordView


urlpatterns = [
    path('signup/', SignupView.as_view(), name='identity-signup'),
    path('signin/', SigninView.as_view(), name='identity-signin'),
    path('recover-password/', RecoverPasswordView.as_view(), name='identity-recover-password'),
]
