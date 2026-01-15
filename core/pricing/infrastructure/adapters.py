from __future__ import annotations

from typing import Iterable, List, Optional
from uuid import UUID, uuid4

from django import forms
from django.contrib import admin
from django.utils import timezone

from core.pricing.domain.entities import Plan
from core.pricing.domain.exceptions import InvalidPlanStateError
from core.pricing.domain.value_objects import BillingCycle, Money, PlanLimit, PricingRule
from core.pricing.repositories.interfaces import PlanRepository

from .django_models import PlanModel


def _deserialize_limits(raw_limits: Iterable[dict]) -> List[PlanLimit]:
    limits: List[PlanLimit] = []
    for item in raw_limits or []:
        limits.append(
            PlanLimit(
                code=item.get("code", ""),
                description=item.get("description", ""),
                value=int(item.get("value", 0)),
                period=item.get("period"),
            )
        )
    return limits


def _deserialize_pricing_rules(raw_rules: Iterable[dict]) -> List[PricingRule]:
    rules: List[PricingRule] = []
    for item in raw_rules or []:
        rules.append(
            PricingRule(
                name=item.get("name", ""),
                rule_type=item.get("rule_type", ""),
                configuration=item.get("configuration", {}),
            )
        )
    return rules


def _serialize_limits(limits: Iterable[PlanLimit]) -> List[dict]:
    return [
        {
            "code": limit.code,
            "description": limit.description,
            "value": limit.value,
            "period": limit.period,
        }
        for limit in limits
    ]


def _serialize_pricing_rules(rules: Iterable[PricingRule]) -> List[dict]:
    return [
        {
            "name": rule.name,
            "rule_type": rule.rule_type,
            "configuration": rule.configuration,
        }
        for rule in rules
    ]


def _plan_model_to_domain(instance: PlanModel) -> Plan:
    try:
        cycle = BillingCycle(instance.billing_cycle)
    except ValueError as exc:  # pragma: no cover - misconfigured data
        raise InvalidPlanStateError(str(exc)) from exc
    return Plan(
        id=instance.id,
        code=instance.code,
        name=instance.name,
        description=instance.description,
        price=Money(amount=instance.amount, currency=instance.currency),
        billing_cycle=cycle,
        limits=_deserialize_limits(instance.limits),
        pricing_rules=_deserialize_pricing_rules(instance.pricing_rules),
        is_active=instance.is_active,
        metadata=instance.metadata or {},
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


def _apply_domain_to_model(plan: Plan, instance: Optional[PlanModel] = None) -> PlanModel:
    if instance is None:
        instance = PlanModel(id=plan.id)
    instance.code = plan.code
    instance.name = plan.name
    instance.description = plan.description
    instance.currency = plan.price.currency
    instance.amount = plan.price.amount
    instance.billing_cycle = plan.billing_cycle.value
    instance.limits = _serialize_limits(plan.limits)
    instance.pricing_rules = _serialize_pricing_rules(plan.pricing_rules)
    instance.metadata = plan.metadata
    instance.is_active = plan.is_active
    return instance


class DjangoORMPlanRepository(PlanRepository):
    """Concrete repository backed by Django ORM."""

    def list_all(self) -> Iterable[Plan]:
        return [_plan_model_to_domain(plan) for plan in PlanModel.objects.all()]

    def get_by_code(self, code: str) -> Optional[Plan]:
        try:
            instance = PlanModel.objects.get(code=code)
        except PlanModel.DoesNotExist:
            return None
        return _plan_model_to_domain(instance)

    def get_by_id(self, plan_id: UUID) -> Optional[Plan]:
        try:
            instance = PlanModel.objects.get(id=plan_id)
        except PlanModel.DoesNotExist:
            return None
        return _plan_model_to_domain(instance)

    def save(self, plan: Plan) -> Plan:
        instance = None
        try:
            instance = PlanModel.objects.get(id=plan.id)
        except PlanModel.DoesNotExist:
            instance = None
        instance = _apply_domain_to_model(plan, instance)
        instance.save()
        return _plan_model_to_domain(instance)

    def delete(self, plan: Plan) -> None:
        PlanModel.objects.filter(id=plan.id).delete()


class PlanAdminForm(forms.ModelForm):
    """Custom admin form to provide structured editing for limits and pricing rules."""

    amount = forms.DecimalField(decimal_places=2, max_digits=12)

    class Meta:
        model = PlanModel
        fields = [
            "code",
            "name",
            "description",
            "currency",
            "amount",
            "billing_cycle",
            "limits",
            "pricing_rules",
            "metadata",
            "is_active",
        ]

    def clean_limits(self):
        limits = self.cleaned_data.get("limits") or []
        normalized: List[dict] = []
        for index, item in enumerate(limits):
            if not isinstance(item, dict):
                raise forms.ValidationError(f"Limit entry #{index + 1} must be an object")
            # Accept both "code" and "key" for flexibility
            code = (item.get("code") or item.get("key") or "").strip()
            if not code:
                raise forms.ValidationError(f"Limit entry #{index + 1} requires a 'code' or 'key' field")
            # Accept both "description" and "name"
            description = item.get("description") or item.get("name") or ""
            normalized.append(
                {
                    "code": code,
                    "description": description,
                    "value": int(item.get("value", 0)),
                    "period": item.get("period"),
                }
            )
        return normalized

    def clean_pricing_rules(self):
        rules = self.cleaned_data.get("pricing_rules") or []
        normalized: List[dict] = []
        for index, item in enumerate(rules):
            if not isinstance(item, dict):
                raise forms.ValidationError(f"Pricing rule #{index + 1} must be an object")
            name = (item.get("name") or "").strip()
            if not name:
                raise forms.ValidationError(f"Pricing rule #{index + 1} requires a name")
            normalized.append(
                {
                    "name": name,
                    "rule_type": item.get("rule_type", ""),
                    "configuration": item.get("configuration", {}),
                }
            )
        return normalized


class PlanAdminAdapter(admin.ModelAdmin):
    """Django admin interface used as the only CRUD entry point for plans."""

    form = PlanAdminForm
    list_display = ("code", "name", "billing_cycle", "amount", "currency", "is_active", "updated_at")
    list_filter = ("billing_cycle", "currency", "is_active")
    search_fields = ("code", "name")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description")}),
        (
            "Pricing",
            {
                "fields": (
                    ("currency", "amount"),
                    "billing_cycle",
                    "pricing_rules",
                )
            },
        ),
        ("Limits", {"fields": ("limits",)}),
        ("Metadata", {"fields": ("metadata", "is_active", "created_at", "updated_at")}),
    )

    def get_queryset(self, request):  # type: ignore[override]
        return super().get_queryset(request).order_by("-updated_at")

    def save_model(self, request, obj, form, change):  # type: ignore[override]
        repository = DjangoORMPlanRepository()
        billing_cycle = BillingCycle(obj.billing_cycle)
        plan_id = obj.id or uuid4()
        created_at = obj.created_at or timezone.now()
        updated_at = timezone.now()
        plan = Plan(
            id=plan_id,
            code=obj.code,
            name=obj.name,
            description=obj.description,
            price=Money(amount=obj.amount, currency=obj.currency),
            billing_cycle=billing_cycle,
            limits=_deserialize_limits(obj.limits),
            pricing_rules=_deserialize_pricing_rules(obj.pricing_rules),
            is_active=obj.is_active,
            metadata=obj.metadata or {},
            created_at=created_at,
            updated_at=updated_at,
        )
        saved = repository.save(plan)
        obj.id = saved.id
        obj.created_at = saved.created_at
        obj.updated_at = saved.updated_at
        obj.amount = saved.price.amount
        obj.currency = saved.price.currency

    def delete_model(self, request, obj):  # type: ignore[override]
        repository = DjangoORMPlanRepository()
        plan = _plan_model_to_domain(obj)
        repository.delete(plan)


def register_admin(admin_site: admin.AdminSite) -> None:
    """Register the Plan admin adapter with the provided admin site."""
    try:
        admin_site.register(PlanModel, PlanAdminAdapter)
    except admin.sites.AlreadyRegistered:
        # Allow reloads without crashing
        pass
