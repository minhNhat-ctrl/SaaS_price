"""
Django Repository Implementations (Tenant)

Infrastructure layer for tenant-owned data.
Shared data repositories are in products_shared module.
"""
from typing import Optional, List
from uuid import UUID
from django.db.models import Q
from django_tenants.utils import schema_context, get_public_schema_name
from core.tenants.infrastructure.django_models import Tenant

from services.products.domain import (
    Product as ProductEntity,
    ProductURLMapping as ProductURLMappingEntity,
    ProductStatus,
)
from services.products.repositories import (
    ProductRepository,
    ProductURLMappingRepository,
)
from services.products.infrastructure.django_models import (
    Product as ProductModel,
    ProductURLMapping as ProductURLMappingModel,
)


# ============================================================
# Helper Functions
# ============================================================

def get_tenant_schema_name(tenant_id: UUID) -> Optional[str]:
    """Get tenant schema name from tenant_id."""
    try:
        with schema_context(get_public_schema_name()):
            tenant = Tenant.objects.get(id=tenant_id)
            return tenant.schema_name
    except Tenant.DoesNotExist:
        return None


# ============================================================
# Mappers (ORM <-> Domain)
# ============================================================

class ProductMapper:
    """Maps between Product domain entity and Django model."""
    
    @staticmethod
    def _parse_status(status_value) -> ProductStatus:
        """Parse status from DB, handling both uppercase and lowercase values."""
        if not status_value:
            return ProductStatus.ACTIVE
        if isinstance(status_value, ProductStatus):
            return status_value
        # Normalize to uppercase to match enum values
        normalized = str(status_value).upper()
        try:
            return ProductStatus(normalized)
        except ValueError:
            return ProductStatus.ACTIVE
    
    @staticmethod
    def to_entity(model: ProductModel) -> ProductEntity:
        """Convert Django model to domain entity."""
        return ProductEntity(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            sku=model.sku,
            gtin=model.gtin,
            status=ProductMapper._parse_status(model.status),
            custom_attributes=model.custom_attributes or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    @staticmethod
    def to_model(entity: ProductEntity) -> ProductModel:
        """Convert domain entity to Django model."""
        return ProductModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            name=entity.name,
            sku=entity.sku,
            gtin=entity.gtin,
            status=entity.status.value if isinstance(entity.status, ProductStatus) else entity.status,
            custom_attributes=entity.custom_attributes or {},
        )
    
    @staticmethod
    def update_model(model: ProductModel, entity: ProductEntity) -> ProductModel:
        """Update Django model from domain entity."""
        model.name = entity.name
        model.sku = entity.sku
        model.gtin = entity.gtin
        model.status = entity.status.value if isinstance(entity.status, ProductStatus) else entity.status
        model.custom_attributes = entity.custom_attributes or {}
        return model


class ProductURLMappingMapper:
    """Maps between ProductURLMapping domain entity and Django model."""
    
    @staticmethod
    def to_entity(model: ProductURLMappingModel) -> ProductURLMappingEntity:
        """Convert Django model to domain entity."""
        return ProductURLMappingEntity(
            id=model.id,
            product_id=model.product_id,
            url_hash=model.url_hash,
            custom_label=model.custom_label,
            is_primary=model.is_primary,
            display_order=model.display_order,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    @staticmethod
    def to_model(entity: ProductURLMappingEntity, product: ProductModel = None) -> ProductURLMappingModel:
        """Convert domain entity to Django model."""
        model = ProductURLMappingModel(
            id=entity.id,
            url_hash=entity.url_hash,
            custom_label=entity.custom_label,
            is_primary=entity.is_primary,
            display_order=entity.display_order,
        )
        if product:
            model.product = product
        return model
    
    @staticmethod
    def update_model(model: ProductURLMappingModel, entity: ProductURLMappingEntity) -> ProductURLMappingModel:
        """Update Django model from domain entity."""
        model.custom_label = entity.custom_label
        model.is_primary = entity.is_primary
        model.display_order = entity.display_order
        return model


# ============================================================
# Repository Implementations
# ============================================================

class DjangoProductRepository(ProductRepository):
    """Django implementation of ProductRepository."""
    
    def create(self, product: ProductEntity) -> ProductEntity:
        """Create a new product."""
        schema = get_tenant_schema_name(product.tenant_id)
        if not schema:
            raise ValueError(f"Tenant {product.tenant_id} not found")
        
        with schema_context(schema):
            model = ProductMapper.to_model(product)
            model.save()
            return ProductMapper.to_entity(model)
    
    def get_by_id(self, product_id: UUID, tenant_id: UUID) -> Optional[ProductEntity]:
        """Get product by ID within tenant."""
        schema = get_tenant_schema_name(tenant_id)
        if not schema:
            return None
        
        with schema_context(schema):
            try:
                model = ProductModel.objects.get(id=product_id, tenant_id=tenant_id)
                return ProductMapper.to_entity(model)
            except ProductModel.DoesNotExist:
                return None
    
    def get_by_sku(self, sku: str, tenant_id: UUID) -> Optional[ProductEntity]:
        """Get product by SKU within tenant."""
        schema = get_tenant_schema_name(tenant_id)
        if not schema:
            return None
        
        with schema_context(schema):
            try:
                model = ProductModel.objects.get(sku=sku, tenant_id=tenant_id)
                return ProductMapper.to_entity(model)
            except ProductModel.DoesNotExist:
                return None
    
    def get_by_gtin(self, gtin: str, tenant_id: UUID) -> Optional[ProductEntity]:
        """Get product by GTIN within tenant."""
        schema = get_tenant_schema_name(tenant_id)
        if not schema:
            return None
        
        with schema_context(schema):
            try:
                model = ProductModel.objects.get(gtin=gtin, tenant_id=tenant_id)
                return ProductMapper.to_entity(model)
            except ProductModel.DoesNotExist:
                return None
    
    def list_by_tenant(
        self,
        tenant_id: UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ProductEntity]:
        """List products for tenant."""
        schema = get_tenant_schema_name(tenant_id)
        if not schema:
            return []
        
        with schema_context(schema):
            queryset = ProductModel.objects.filter(tenant_id=tenant_id)
            
            if status:
                queryset = queryset.filter(status=status)
            
            queryset = queryset.order_by('-created_at')
            models = queryset[offset:offset + limit]
            return [ProductMapper.to_entity(m) for m in models]
    
    def update(self, product: ProductEntity) -> ProductEntity:
        """Update product."""
        schema = get_tenant_schema_name(product.tenant_id)
        if not schema:
            raise ValueError(f"Tenant {product.tenant_id} not found")
        
        with schema_context(schema):
            model = ProductModel.objects.get(id=product.id, tenant_id=product.tenant_id)
            model = ProductMapper.update_model(model, product)
            model.save()
            return ProductMapper.to_entity(model)
    
    def delete(self, product_id: UUID, tenant_id: UUID) -> bool:
        """Delete product and all its URL mappings (via cascade)."""
        schema = get_tenant_schema_name(tenant_id)
        if not schema:
            return False
        
        with schema_context(schema):
            deleted, _ = ProductModel.objects.filter(
                id=product_id,
                tenant_id=tenant_id
            ).delete()
            return deleted > 0
    
    def search(
        self,
        tenant_id: UUID,
        query: str,
        limit: int = 50
    ) -> List[ProductEntity]:
        """Search products by name, SKU, or GTIN."""
        schema = get_tenant_schema_name(tenant_id)
        if not schema:
            return []
        
        with schema_context(schema):
            queryset = ProductModel.objects.filter(
                tenant_id=tenant_id
            ).filter(
                Q(name__icontains=query) |
                Q(sku__icontains=query) |
                Q(gtin__icontains=query)
            )[:limit]
            
            return [ProductMapper.to_entity(m) for m in queryset]
    
    def exists_by_sku(self, sku: str, tenant_id: UUID) -> bool:
        """Check if SKU exists for tenant."""
        schema = get_tenant_schema_name(tenant_id)
        if not schema:
            return False
        
        with schema_context(schema):
            return ProductModel.objects.filter(sku=sku, tenant_id=tenant_id).exists()
    
    def exists_by_gtin(self, gtin: str, tenant_id: UUID) -> bool:
        """Check if GTIN exists for tenant."""
        schema = get_tenant_schema_name(tenant_id)
        if not schema:
            return False
        
        with schema_context(schema):
            return ProductModel.objects.filter(gtin=gtin, tenant_id=tenant_id).exists()
    
    def count_by_tenant(self, tenant_id: UUID) -> int:
        """Count products for tenant."""
        schema = get_tenant_schema_name(tenant_id)
        if not schema:
            return 0
        
        with schema_context(schema):
            return ProductModel.objects.filter(tenant_id=tenant_id).count()


class DjangoProductURLMappingRepository(ProductURLMappingRepository):
    """
    Django implementation of ProductURLMappingRepository.
    
    Operates within tenant schema.
    Uses url_hash to reference shared ProductURL in public schema.
    """
    
    def __init__(self, tenant_id: UUID = None):
        self._tenant_id = tenant_id
    
    def set_tenant(self, tenant_id: UUID):
        """Set current tenant context."""
        self._tenant_id = tenant_id
    
    def _get_schema(self) -> Optional[str]:
        if not self._tenant_id:
            return None
        return get_tenant_schema_name(self._tenant_id)
    
    def create(self, mapping: ProductURLMappingEntity) -> ProductURLMappingEntity:
        """Create a new URL mapping."""
        schema = self._get_schema()
        if not schema:
            raise ValueError("Tenant context required for URL mapping operations")
        
        with schema_context(schema):
            # Get the product
            try:
                product = ProductModel.objects.get(id=mapping.product_id)
            except ProductModel.DoesNotExist:
                raise ValueError(f"Product {mapping.product_id} not found")
            
            model = ProductURLMappingMapper.to_model(mapping, product)
            model.save()
            return ProductURLMappingMapper.to_entity(model)
    
    def get_by_id(self, mapping_id: UUID) -> Optional[ProductURLMappingEntity]:
        """Get mapping by ID."""
        schema = self._get_schema()
        if not schema:
            return None
        
        with schema_context(schema):
            try:
                model = ProductURLMappingModel.objects.get(id=mapping_id)
                return ProductURLMappingMapper.to_entity(model)
            except ProductURLMappingModel.DoesNotExist:
                return None
    
    def get_by_product_and_hash(
        self,
        product_id: UUID,
        url_hash: str
    ) -> Optional[ProductURLMappingEntity]:
        """Get mapping by product and URL hash."""
        schema = self._get_schema()
        if not schema:
            return None
        
        with schema_context(schema):
            try:
                model = ProductURLMappingModel.objects.get(
                    product_id=product_id,
                    url_hash=url_hash
                )
                return ProductURLMappingMapper.to_entity(model)
            except ProductURLMappingModel.DoesNotExist:
                return None
    
    def list_by_product(self, product_id: UUID) -> List[ProductURLMappingEntity]:
        """List all URL mappings for a product."""
        schema = self._get_schema()
        if not schema:
            return []
        
        with schema_context(schema):
            models = ProductURLMappingModel.objects.filter(
                product_id=product_id
            ).order_by('display_order', '-is_primary')
            return [ProductURLMappingMapper.to_entity(m) for m in models]
    
    def list_by_tenant(
        self,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[ProductURLMappingEntity]:
        """List all URL mappings for a tenant."""
        schema = get_tenant_schema_name(tenant_id)
        if not schema:
            return []
        
        with schema_context(schema):
            models = ProductURLMappingModel.objects.all().order_by(
                '-created_at'
            )[offset:offset + limit]
            return [ProductURLMappingMapper.to_entity(m) for m in models]
    
    def update(self, mapping: ProductURLMappingEntity) -> ProductURLMappingEntity:
        """Update URL mapping."""
        schema = self._get_schema()
        if not schema:
            raise ValueError("Tenant context required for URL mapping operations")
        
        with schema_context(schema):
            model = ProductURLMappingModel.objects.get(id=mapping.id)
            model = ProductURLMappingMapper.update_model(model, mapping)
            model.save()
            return ProductURLMappingMapper.to_entity(model)
    
    def delete(self, mapping_id: UUID) -> bool:
        """Delete URL mapping."""
        schema = self._get_schema()
        if not schema:
            return False
        
        with schema_context(schema):
            try:
                model = ProductURLMappingModel.objects.get(id=mapping_id)
                url_hash = model.url_hash
                model.delete()
                return True
            except ProductURLMappingModel.DoesNotExist:
                return False
    
    def delete_by_product(self, product_id: UUID) -> List[str]:
        """
        Delete all mappings for a product.
        Returns list of url_hashes for reference cleanup.
        """
        schema = self._get_schema()
        if not schema:
            return []
        
        with schema_context(schema):
            models = ProductURLMappingModel.objects.filter(product_id=product_id)
            url_hashes = list(models.values_list('url_hash', flat=True))
            models.delete()
            return url_hashes
    
    def exists_for_tenant(self, tenant_id: UUID, url_hash: str) -> bool:
        """
        Check if tenant already has this URL mapped (to any product).
        """
        schema = get_tenant_schema_name(tenant_id)
        if not schema:
            return False
        
        with schema_context(schema):
            return ProductURLMappingModel.objects.filter(url_hash=url_hash).exists()
    
    def get_primary_for_product(self, product_id: UUID) -> Optional[ProductURLMappingEntity]:
        """Get the primary URL mapping for a product."""
        schema = self._get_schema()
        if not schema:
            return None
        
        with schema_context(schema):
            try:
                model = ProductURLMappingModel.objects.get(
                    product_id=product_id,
                    is_primary=True
                )
                return ProductURLMappingMapper.to_entity(model)
            except ProductURLMappingModel.DoesNotExist:
                return None
    
    def set_primary(self, mapping_id: UUID, product_id: UUID) -> bool:
        """
        Set a mapping as primary, unset other primary mappings for the product.
        """
        schema = self._get_schema()
        if not schema:
            return False
        
        with schema_context(schema):
            # Unset all primary flags for this product
            ProductURLMappingModel.objects.filter(
                product_id=product_id,
                is_primary=True
            ).update(is_primary=False)
            
            # Set the specified mapping as primary
            updated = ProductURLMappingModel.objects.filter(
                id=mapping_id,
                product_id=product_id
            ).update(is_primary=True)
            
            return updated > 0
    
    def count_by_hash(self, url_hash: str) -> int:
        """
        Count how many tenants have mapped this URL.
        Note: This is best handled by products_shared.ProductURL.reference_count
        """
        # This would require iterating through all tenant schemas
        # For performance, use ProductURL.reference_count instead
        raise NotImplementedError(
            "Use products_shared.ProductURL.reference_count for cross-tenant URL counting"
        )
