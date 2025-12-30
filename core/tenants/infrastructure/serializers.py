"""
Serializers cho Tenant API

Mục đích:
- Validate input từ HTTP request
- Serialize domain objects → JSON response
- Mapping giữa request data ↔ domain objects
"""
from rest_framework import serializers
from core.tenants.domain import Tenant, TenantStatus


class TenantDomainSerializer(serializers.Serializer):
    """Serializer cho TenantDomain value object"""
    domain = serializers.CharField(max_length=255)
    is_primary = serializers.BooleanField(default=True)


class TenantSerializer(serializers.Serializer):
    """Serializer cho Tenant (read/response)"""
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=100)
    status = serializers.ChoiceField(choices=[s.value for s in TenantStatus])
    domains = TenantDomainSerializer(many=True, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        """
        Convert domain Tenant entity → JSON
        
        Args:
            instance: Domain Tenant entity
        
        Returns:
            Dict ready for JSON serialization
        """
        if isinstance(instance, Tenant):
            return {
                'id': str(instance.id),
                'name': instance.name,
                'slug': instance.slug,
                'status': instance.status.value,
                'domains': [
                    {
                        'domain': d.domain,
                        'is_primary': d.is_primary,
                    }
                    for d in instance.domains
                ],
                'created_at': instance.created_at.isoformat(),
                'updated_at': instance.updated_at.isoformat(),
            }
        return super().to_representation(instance)


class CreateTenantSerializer(serializers.Serializer):
    """Serializer cho tạo tenant mới (write/request)"""
    name = serializers.CharField(max_length=255, required=True)
    slug = serializers.SlugField(max_length=100, required=True)
    domain = serializers.CharField(max_length=255, required=True)
    is_primary = serializers.BooleanField(default=True, required=False)

    def validate_name(self, value):
        """Validate name không rỗng"""
        if not value.strip():
            raise serializers.ValidationError("Name cannot be empty")
        return value.strip()

    def validate_slug(self, value):
        """Validate slug format"""
        if not value.strip():
            raise serializers.ValidationError("Slug cannot be empty")
        return value.strip().lower()


class UpdateTenantSerializer(serializers.Serializer):
    """Serializer cho cập nhật tenant (partial update)"""
    name = serializers.CharField(max_length=255, required=False)
    
    def validate_name(self, value):
        """Validate name"""
        if value and not value.strip():
            raise serializers.ValidationError("Name cannot be empty")
        return value.strip() if value else None


class AddDomainSerializer(serializers.Serializer):
    """Serializer cho thêm domain mới"""
    domain = serializers.CharField(max_length=255, required=True)
    is_primary = serializers.BooleanField(default=False, required=False)
