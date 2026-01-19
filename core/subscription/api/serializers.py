from rest_framework import serializers

from core.subscription.dto import SubscriptionSummary


class SubscriptionSerializer(serializers.Serializer):
    """Serializer for subscription data transfer."""

    id = serializers.CharField()
    tenant_id = serializers.CharField()
    plan_code = serializers.CharField()
    status = serializers.CharField()
    start_date = serializers.CharField()
    end_date = serializers.CharField()
    created_at = serializers.CharField()
    updated_at = serializers.CharField()

    @staticmethod
    def from_dto(dto: SubscriptionSummary) -> dict:
        return {
            "id": str(dto.id),
            "tenant_id": str(dto.tenant_id),
            "plan_code": dto.plan_code,
            "status": dto.status.value,
            "start_date": dto.start_date.isoformat(),
            "end_date": dto.end_date.isoformat(),
            "created_at": dto.created_at.isoformat(),
            "updated_at": dto.updated_at.isoformat(),
        }
