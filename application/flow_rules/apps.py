"""Application flow rule app configuration."""
from __future__ import annotations

from django.apps import AppConfig


class FlowRulesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'application.flow_rules'
    verbose_name = 'Application Flow Toggles'

    def ready(self) -> None:
        from .infrastructure import django_admin  # noqa: import inside ready

        django_admin.register_admin()
