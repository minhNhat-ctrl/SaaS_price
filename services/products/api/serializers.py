"""
API Serializers

Validates input and formats output for API endpoints.
Based on PRODUCTS_DATA_CONTRACT.md architecture.
"""
from rest_framework import serializers


# ============================================================
# Product Serializers (Tenant Data)
# ============================================================

STATUS_CHOICES = [
    ('ACTIVE', 'Active'),
    ('ARCHIVED', 'Archived'),
    ('DRAFT', 'Draft'),
    ('DISCONTINUED', 'Discontinued'),
]


class ProductSerializer(serializers.Serializer):
    """Serializer for Product entity."""
    
    id = serializers.UUIDField(read_only=True)
    tenant_id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=255)
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True)
    gtin = serializers.CharField(max_length=50, required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )
    custom_attributes = serializers.JSONField(required=False, default=dict)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ProductCreateSerializer(serializers.Serializer):
    """Serializer for creating a product."""
    
    name = serializers.CharField(max_length=255)
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    gtin = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    status = serializers.ChoiceField(
        choices=STATUS_CHOICES,
        default='ACTIVE',
        required=False
    )
    custom_attributes = serializers.JSONField(required=False, default=dict)


class ProductUpdateSerializer(serializers.Serializer):
    """Serializer for updating a product."""
    
    name = serializers.CharField(max_length=255, required=False)
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True)
    gtin = serializers.CharField(max_length=50, required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=STATUS_CHOICES,
        required=False
    )
    custom_attributes = serializers.JSONField(required=False)


# ============================================================
# URL Mapping Serializers (Tenant Data)
# ============================================================

class ProductURLMappingSerializer(serializers.Serializer):
    """Serializer for ProductURLMapping entity."""
    
    id = serializers.UUIDField(read_only=True)
    product_id = serializers.UUIDField(read_only=True)
    url_hash = serializers.CharField(read_only=True)
    custom_label = serializers.CharField(max_length=255, required=False, allow_blank=True)
    is_primary = serializers.BooleanField(default=False)
    display_order = serializers.IntegerField(default=0)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class AddURLToProductSerializer(serializers.Serializer):
    """Serializer for adding URL to product."""
    
    raw_url = serializers.URLField()
    custom_label = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    is_primary = serializers.BooleanField(default=False, required=False)


# ============================================================
# ProductURL Serializers (Shared Data)
# ============================================================

class ProductURLSerializer(serializers.Serializer):
    """Serializer for ProductURL entity (shared)."""
    
    id = serializers.UUIDField(read_only=True)
    raw_url = serializers.CharField()
    normalized_url = serializers.CharField(read_only=True)
    url_hash = serializers.CharField(read_only=True)
    domain = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    reference_count = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ProductURLInfoSerializer(serializers.Serializer):
    """Serializer for combined mapping + URL info."""
    
    mapping = ProductURLMappingSerializer()
    url = ProductURLSerializer()


# ============================================================
# Price History Serializers (Shared Data)
# ============================================================

class PriceHistorySerializer(serializers.Serializer):
    """Serializer for PriceHistory entity."""
    
    id = serializers.UUIDField(read_only=True)
    url_hash = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(max_length=10, default='JPY')
    original_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    source = serializers.ChoiceField(
        choices=['crawler', 'api', 'manual', 'import'],
        default='crawler'
    )
    is_available = serializers.BooleanField(default=True)
    stock_status = serializers.CharField(max_length=50, required=False, allow_blank=True)
    scraped_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField(read_only=True)
    discount_percentage = serializers.SerializerMethodField()
    
    def get_discount_percentage(self, obj):
        """Calculate discount percentage."""
        if hasattr(obj, 'calculate_discount_percentage'):
            return obj.calculate_discount_percentage()
        return None


# ============================================================
# Combined Response Serializers
# ============================================================

class ProductWithURLsSerializer(serializers.Serializer):
    """Serializer for product with its URLs."""
    
    product = ProductSerializer()
    urls = ProductURLInfoSerializer(many=True)


# Legacy aliases for backward compatibility
ProductURLOwnershipSerializer = ProductURLMappingSerializer
