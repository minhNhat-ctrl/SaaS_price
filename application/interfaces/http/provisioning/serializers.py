"""Serializers for provisioning flow HTTP adapter."""
from rest_framework import serializers

from application.dto.provisioning import (
    SignupCommand,
    ProvisioningContext,
)


class SignupRequestSerializer(serializers.Serializer):
    """Validates and transforms signup request into SignupCommand DTO."""

    email = serializers.EmailField(
        required=True,
        help_text="User email address"
    )
    password = serializers.CharField(
        required=True,
        min_length=8,
        write_only=True,
        help_text="User password (min 8 characters)"
    )
    source = serializers.CharField(
        required=False,
        default="web",
        help_text="Source of signup (web, mobile, api, etc.)"
    )

    def to_command(self) -> SignupCommand:
        """Transform validated data into SignupCommand DTO."""
        return SignupCommand(
            email=self.validated_data['email'],
            password=self.validated_data['password'],
            source=self.validated_data.get('source', 'web'),
        )


class ProvisioningContextResponseSerializer(serializers.Serializer):
    """Transforms ProvisioningContext into API response."""

    user_id = serializers.CharField(
        required=False,
        allow_null=True,
        read_only=True,
        help_text="Created user ID"
    )
    tenant_id = serializers.CharField(
        required=False,
        allow_null=True,
        read_only=True,
        help_text="Created tenant ID"
    )
    plan_code = serializers.CharField(
        required=False,
        allow_null=True,
        read_only=True,
        help_text="Assigned plan code"
    )
    subscription_status = serializers.CharField(
        required=False,
        allow_null=True,
        read_only=True,
        help_text="Subscription status (trial, active, etc.)"
    )
    quote_id = serializers.CharField(
        required=False,
        allow_null=True,
        read_only=True,
        help_text="Payment quote ID (if required)"
    )
    requires_payment = serializers.BooleanField(
        required=False,
        read_only=True,
        help_text="Whether payment is required"
    )
    metadata = serializers.DictField(
        required=False,
        allow_null=True,
        read_only=True,
        help_text="Flow execution metadata"
    )

    @staticmethod
    def from_context(context: ProvisioningContext) -> dict:
        """Convert ProvisioningContext to response dict."""
        return {
            'user_id': context.user_id,
            'tenant_id': context.tenant_id,
            'plan_code': context.plan_code,
            'subscription_status': context.subscription_status,
            'quote_id': context.quote_id,
            'requires_payment': context.requires_payment,
            'metadata': context.metadata,
        }
