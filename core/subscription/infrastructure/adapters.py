from __future__ import annotations

from datetime import date
from typing import Iterable, List, Optional
from uuid import UUID, uuid4

from django import forms
from django.contrib import admin
from django.utils import timezone

from core.subscription.domain.entities import Subscription
from core.subscription.domain.value_objects import DateRange, SubscriptionStatus
from core.subscription.repositories.interfaces import SubscriptionRepository

from .django_models import SubscriptionModel


def _subscription_model_to_domain(instance: SubscriptionModel) -> Subscription:
    try:
        status = SubscriptionStatus(instance.status)
    except ValueError as exc:  # pragma: no cover - misconfigured data
        raise ValueError(str(exc)) from exc
    return Subscription(
        id=instance.id,
        tenant_id=instance.tenant_id,
        plan_code=instance.plan_code,
        date_range=DateRange(start_date=instance.start_date, end_date=instance.end_date),
        status=status,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


def _apply_domain_to_model(subscription: Subscription, instance: Optional[SubscriptionModel] = None) -> SubscriptionModel:
    if instance is None:
        instance = SubscriptionModel(id=subscription.id)
    instance.tenant_id = subscription.tenant_id
    instance.plan_code = subscription.plan_code
    instance.start_date = subscription.date_range.start_date
    instance.end_date = subscription.date_range.end_date
    instance.status = subscription.status.value
    return instance


class DjangoORMSubscriptionRepository(SubscriptionRepository):
    """Concrete repository backed by Django ORM."""

    def list_by_tenant(self, tenant_id: UUID) -> Iterable[Subscription]:
        return [_subscription_model_to_domain(sub) for sub in SubscriptionModel.objects.filter(tenant_id=tenant_id)]

    def get_by_id(self, subscription_id: UUID) -> Optional[Subscription]:
        try:
            instance = SubscriptionModel.objects.get(id=subscription_id)
        except SubscriptionModel.DoesNotExist:
            return None
        return _subscription_model_to_domain(instance)

    def get_active_by_tenant(self, tenant_id: UUID) -> Optional[Subscription]:
        try:
            instance = SubscriptionModel.objects.get(tenant_id=tenant_id, status="active")
        except SubscriptionModel.DoesNotExist:
            return None
        return _subscription_model_to_domain(instance)

    def save(self, subscription: Subscription) -> Subscription:
        instance = None
        try:
            instance = SubscriptionModel.objects.get(id=subscription.id)
        except SubscriptionModel.DoesNotExist:
            instance = None
        instance = _apply_domain_to_model(subscription, instance)
        instance.save()
        return _subscription_model_to_domain(instance)

    def delete(self, subscription: Subscription) -> None:
        SubscriptionModel.objects.filter(id=subscription.id).delete()


class SubscriptionAdminForm(forms.ModelForm):
    """Custom admin form for subscription management."""

    class Meta:
        model = SubscriptionModel
        fields = ["tenant_id", "plan_code", "start_date", "end_date", "status"]


class SubscriptionAdminAdapter(admin.ModelAdmin):
    """Django admin interface for subscription CRUD (admin only)."""

    form = SubscriptionAdminForm
    list_display = ("tenant_id", "plan_code", "status", "start_date", "end_date", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("tenant_id",)
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        ("Identity", {"fields": ("id", "tenant_id")}),
        ("Plan", {"fields": ("plan_code",)}),
        ("Duration", {"fields": (("start_date", "end_date"),)}),
        ("Status", {"fields": ("status",)}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )

    def get_queryset(self, request):  # type: ignore[override]
        return super().get_queryset(request).order_by("-updated_at")

    def save_model(self, request, obj, form, change):  # type: ignore[override]
        repository = DjangoORMSubscriptionRepository()
        subscription = Subscription(
            id=obj.id,
            tenant_id=obj.tenant_id,
            plan_code=obj.plan_code,
            date_range=DateRange(start_date=obj.start_date, end_date=obj.end_date),
            status=SubscriptionStatus(obj.status),
            created_at=obj.created_at or timezone.now(),
            updated_at=timezone.now(),
        )
        saved = repository.save(subscription)
        obj.id = saved.id
        obj.created_at = saved.created_at
        obj.updated_at = saved.updated_at

    def delete_model(self, request, obj):  # type: ignore[override]
        repository = DjangoORMSubscriptionRepository()
        subscription = _subscription_model_to_domain(obj)
        repository.delete(subscription)


def register_admin(admin_site: admin.AdminSite) -> None:
    """Register the Subscription admin adapter with the provided admin site."""

    try:
        admin_site.register(SubscriptionModel, SubscriptionAdminAdapter)
    except admin.sites.AlreadyRegistered:
        # Allow reloads without crashing
        pass
