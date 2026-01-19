"""Admin integration for flow rule toggles."""
from __future__ import annotations

from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered

from .django_models import FlowRuleToggleModel


class FlowRuleToggleAdmin(admin.ModelAdmin):
    list_display = ("flow_code", "step_code", "is_enabled", "updated_at")
    list_filter = ("flow_code", "is_enabled")
    search_fields = ("flow_code", "step_code", "description")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("flow_code", "step_code")
    fieldsets = (
        ("Flow", {"fields": ("flow_code", "step_code")}),
        ("Rule", {"fields": ("is_enabled", "description")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )


def register_admin() -> None:
    try:
        admin.site.register(FlowRuleToggleModel, FlowRuleToggleAdmin)
    except AlreadyRegistered:
        return
