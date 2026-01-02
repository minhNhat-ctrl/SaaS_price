"""
Products API - Serializers for DRF

Convert domain entities to JSON and validate input.
"""
from rest_framework import serializers
from datetime import datetime
from typing import Dict, Any


class ProductURLSerializer(serializers.Serializer):
    """Product URL serializer"""
    id = serializers.UUIDField(read_only=True)
    domain = serializers.CharField(max_length=255)
    full_url = serializers.CharField(max_length=2048)
    marketplace_type = serializers.CharField(max_length=50)
    currency = serializers.CharField(max_length=10, default="USD")
    is_active = serializers.BooleanField(default=True)
    meta = serializers.JSONField(default=dict)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class PriceRecordSerializer(serializers.Serializer):
    """Price record serializer"""
    id = serializers.UUIDField(read_only=True)
    price = serializers.FloatField(min_value=0)
    currency = serializers.CharField(max_length=10)
    source = serializers.CharField(max_length=50, default="manual")
    recorded_at = serializers.DateTimeField()
    meta = serializers.JSONField(default=dict)


class TenantProductSerializer(serializers.Serializer):
    """Tenant product serializer"""
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=255)
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True)
    internal_code = serializers.CharField(max_length=100, required=False, allow_blank=True)
    barcode = serializers.CharField(max_length=100, required=False, allow_blank=True)
    gtin = serializers.CharField(max_length=50, required=False, allow_blank=True)
    brand = serializers.CharField(max_length=100, required=False, allow_blank=True)
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    status = serializers.CharField(max_length=20, default="DRAFT")
    custom_attributes = serializers.JSONField(default=dict)
    is_public = serializers.BooleanField(default=False)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class CreateProductSerializer(serializers.Serializer):
    """Create product request serializer"""
    name = serializers.CharField(max_length=255)
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True)
    internal_code = serializers.CharField(max_length=100, required=False, allow_blank=True)
    barcode = serializers.CharField(max_length=100, required=False, allow_blank=True)
    gtin = serializers.CharField(max_length=50, required=False, allow_blank=True)
    brand = serializers.CharField(max_length=100, required=False, allow_blank=True)
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    custom_attributes = serializers.JSONField(required=False)


class UpdateProductSerializer(serializers.Serializer):
    """Update product request serializer"""
    name = serializers.CharField(max_length=255, required=False)
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True)
    brand = serializers.CharField(max_length=100, required=False, allow_blank=True)
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    custom_attributes = serializers.JSONField(required=False)


class AddProductURLSerializer(serializers.Serializer):
    """Add product URL request serializer"""
    domain = serializers.CharField(max_length=255)
    full_url = serializers.CharField(max_length=2048)
    marketplace_type = serializers.CharField(max_length=50)
    currency = serializers.CharField(max_length=10, default="USD")
    is_primary = serializers.BooleanField(default=False)


class RecordPriceSerializer(serializers.Serializer):
    """Record price request serializer"""
    price = serializers.FloatField(min_value=0)
    currency = serializers.CharField(max_length=10)
    source = serializers.CharField(max_length=50, default="manual")
    meta = serializers.JSONField(required=False)
