"""
Repository Interfaces (Tenant)

Abstract interfaces for tenant-owned data access.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from services.products.domain import (
    Product,
    ProductURLMapping,
)


# ============================================================
# Product Repository (Tenant Schema)
# ============================================================

class ProductRepository(ABC):
    """Repository for tenant-owned products."""
    
    @abstractmethod
    def create(self, product: Product) -> Product:
        """Create a new product."""
        pass
    
    @abstractmethod
    def get_by_id(self, product_id: UUID, tenant_id: UUID) -> Optional[Product]:
        """Get product by ID within tenant."""
        pass
    
    @abstractmethod
    def get_by_sku(self, sku: str, tenant_id: UUID) -> Optional[Product]:
        """Get product by SKU within tenant."""
        pass
    
    @abstractmethod
    def get_by_gtin(self, gtin: str, tenant_id: UUID) -> Optional[Product]:
        """Get product by GTIN within tenant."""
        pass
    
    @abstractmethod
    def list_by_tenant(
        self,
        tenant_id: UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Product]:
        """List products for tenant."""
        pass
    
    @abstractmethod
    def update(self, product: Product) -> Product:
        """Update product."""
        pass
    
    @abstractmethod
    def delete(self, product_id: UUID, tenant_id: UUID) -> bool:
        """Delete product."""
        pass
    
    @abstractmethod
    def search(
        self,
        tenant_id: UUID,
        query: str,
        limit: int = 50
    ) -> List[Product]:
        """Search products by name, SKU, GTIN."""
        pass
    
    @abstractmethod
    def exists_by_sku(self, sku: str, tenant_id: UUID) -> bool:
        """Check if SKU exists for tenant."""
        pass
    
    @abstractmethod
    def exists_by_gtin(self, gtin: str, tenant_id: UUID) -> bool:
        """Check if GTIN exists for tenant."""
        pass
    
    @abstractmethod
    def count_by_tenant(self, tenant_id: UUID) -> int:
        """Count products for tenant."""
        pass


# ============================================================
# ProductURLMapping Repository (Tenant Schema)
# ============================================================

class ProductURLMappingRepository(ABC):
    """Repository for product URL mappings (tenant-owned)."""
    
    @abstractmethod
    def set_tenant(self, tenant_id: UUID) -> None:
        """Set current tenant context."""
        pass
    
    @abstractmethod
    def create(self, mapping: ProductURLMapping) -> ProductURLMapping:
        """Create a new URL mapping."""
        pass
    
    @abstractmethod
    def get_by_id(self, mapping_id: UUID) -> Optional[ProductURLMapping]:
        """Get mapping by ID."""
        pass
    
    @abstractmethod
    def get_by_product_and_hash(
        self,
        product_id: UUID,
        url_hash: str
    ) -> Optional[ProductURLMapping]:
        """Get mapping by product and URL hash."""
        pass
    
    @abstractmethod
    def list_by_product(self, product_id: UUID) -> List[ProductURLMapping]:
        """List all URL mappings for a product."""
        pass
    
    @abstractmethod
    def list_by_tenant(
        self,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[ProductURLMapping]:
        """List all URL mappings for a tenant."""
        pass
    
    @abstractmethod
    def update(self, mapping: ProductURLMapping) -> ProductURLMapping:
        """Update URL mapping."""
        pass
    
    @abstractmethod
    def delete(self, mapping_id: UUID) -> bool:
        """Delete URL mapping."""
        pass
    
    @abstractmethod
    def delete_by_product(self, product_id: UUID) -> List[str]:
        """Delete all mappings for a product. Returns list of url_hashes."""
        pass
    
    @abstractmethod
    def exists_for_tenant(self, tenant_id: UUID, url_hash: str) -> bool:
        """Check if tenant already has this URL mapped (to any product)."""
        pass
    
    @abstractmethod
    def get_primary_for_product(self, product_id: UUID) -> Optional[ProductURLMapping]:
        """Get the primary URL mapping for a product."""
        pass
    
    @abstractmethod
    def set_primary(self, mapping_id: UUID, product_id: UUID) -> bool:
        """Set a mapping as primary."""
        pass
