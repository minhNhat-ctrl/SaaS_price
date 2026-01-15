"""Serializers for pricing plans (placeholder for future API exposure)."""

from rest_framework import serializers


class PlanSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    currency = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    billing_cycle = serializers.CharField()
    limits = serializers.JSONField()
    pricing_rules = serializers.JSONField()

    @staticmethod
    def from_service(plan) -> dict:
        return {
            "code": plan.code,
            "name": plan.name,
            "description": plan.description,
            "currency": plan.currency,
            "amount": plan.amount,
            "billing_cycle": plan.billing_cycle,
            "limits": plan.limits,
            "pricing_rules": plan.pricing_rules,
        }
