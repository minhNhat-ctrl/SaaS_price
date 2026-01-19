"""URL configuration for Accounts module."""

from core.accounts.api import urls as api_urls

app_name = api_urls.app_name
urlpatterns = api_urls.urlpatterns
