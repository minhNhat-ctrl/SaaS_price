from rest_framework import serializers

from core.subscription.services.use_cases import SubscriptionDTO


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
    def from_dto(dto: SubscriptionDTO) -> dict:
        return {
            "id": dto.id,
            "tenant_id": dto.tenant_id,
            "plan_code": dto.plan_code,
            "status": dto.status,
            "start_date": dto.start_date,
            "end_date": dto.end_date,
            "created_at": dto.created_at,
            "updated_at": dto.updated_at,
        }
