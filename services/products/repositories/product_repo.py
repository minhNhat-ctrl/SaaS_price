"""
Product Repositories - Data Access Interfaces

Abstract interfaces - no implementation details.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from services.products.domain import (
    TenantProduct,
    SharedProduct,
    SharedProductURL,
    SharedPriceHistory,
)


# ============================================================
# Tenant Product Repository (Tenant Schema)
# ============================================================

class TenantProductRepository(ABC):
    """Repository for tenant-owned products."""
    
    @abstractmethod
    async def create(self, product: TenantProduct) -> TenantProduct:
        """Create a new tenant product."""
        pass
    
    @abstractmethod
    async def get_by_id(self, product_id: UUID, tenant_id: UUID) -> Optional[TenantProduct]:
        """Get product by ID within tenant."""
        pass
    
    @abstractmethod
    async def get_by_sku(self, sku: str, tenant_id: UUID) -> Optional[TenantProduct]:
        """Get product by SKU within tenant."""
        pass
    
    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TenantProduct]:
        """List products for tenant."""
        pass
    
    @abstractmethod
    async def update(self, product: TenantProduct) -> TenantProduct:
        """Update product."""
        pass
    
    @abstractmethod
    async def delete(self, product_id: UUID, tenant_id: UUID) -> bool:
        """Delete product."""
        pass
    
    @abstractmethod
    async def search(
        self,
        tenant_id: UUID,
        query: str,
        limit: int = 50
    ) -> List[TenantProduct]:
        """Search products by name, SKU, barcode."""
        pass


# ============================================================
# Shared Product Repository (Public Schema)
# ============================================================

class SharedProductRepository(ABC):
    """Repository for shared/canonical products."""
    
    @abstractmethod
    async def create(self, product: SharedProduct) -> SharedProduct:
        """Create a new shared product."""
        pass
    
    @abstractmethod
    async def get_by_id(self, product_id: UUID) -> Optional[SharedProduct]:
        """Get shared product by ID."""
        pass
    
    @abstractmethod
    async def get_by_gtin(self, gtin: str) -> Optional[SharedProduct]:
        """Get shared product by GTIN."""
        pass
    
    @abstractmethod
    async def find_or_create_by_identifiers(
        self,
        gtin: str = "",
        ean: str = "",
        upc: str = "",
        manufacturer: str = "",
        normalized_name: str = ""
    ) -> SharedProduct:
        """Find existing or create new shared product."""
        pass
    
    @abstractmethod
    async def update(self, product: SharedProduct) -> SharedProduct:
        """Update shared product."""
        pass
    
    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[SharedProduct]:
        """List all shared products."""
        pass


# ============================================================
# Product URL Repository (Public Schema)
# ============================================================

class SharedProductURLRepository(ABC):
    """Repository for product URLs."""
    
    @abstractmethod
    async def create(self, product_url: SharedProductURL) -> SharedProductURL:
        """Create a new product URL."""
        pass
    
    @abstractmethod
    async def get_by_id(self, url_id: UUID) -> Optional[SharedProductURL]:
        """Get product URL by ID."""
        pass
    
    @abstractmethod
    async def get_by_url(self, full_url: str) -> Optional[SharedProductURL]:
        """Get product URL by full URL string."""
        pass
    
    @abstractmethod
    async def list_by_product(
        self,
        product_id: UUID,
        is_active: Optional[bool] = None
    ) -> List[SharedProductURL]:
        """List all URLs for a shared product."""
        pass
    
    @abstractmethod
    async def list_by_marketplace(
        self,
        marketplace_type: str,
        is_active: bool = True,
        limit: int = 100
    ) -> List[SharedProductURL]:
        """List URLs by marketplace type."""
        pass
    
    @abstractmethod
    async def update(self, product_url: SharedProductURL) -> SharedProductURL:
        """Update product URL."""
        pass
    
    @abstractmethod
    async def delete(self, url_id: UUID) -> bool:
        """Delete product URL."""
        pass


# ============================================================
# Tenant URL Tracking Repository (Tenant Schema)
# ============================================================

class TenantProductURLTrackingRepository(ABC):
    """Repository for tenant URL tracking data."""
    
    @abstractmethod
    async def create(self, tracking: 'TenantProductURLTracking') -> 'TenantProductURLTracking':
        """Create a new tracking record."""
        pass
    
    @abstractmethod
    async def get_by_id(self, tracking_id: UUID, tenant_id: UUID) -> Optional['TenantProductURLTracking']:
        """Get tracking record by ID."""
        pass
    
    @abstractmethod
    async def get_by_tenant_and_url(
        self,
        tenant_id: UUID,
        shared_url_id: UUID
    ) -> Optional['TenantProductURLTracking']:
        """Get tracking record by tenant and shared URL."""
        pass
    
    @abstractmethod
    async def list_by_product(
        self,
        product_id: UUID,
        tenant_id: UUID
    ) -> List['TenantProductURLTracking']:
        """List all URLs tracked by a tenant product."""
        pass
    
    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID) -> List['TenantProductURLTracking']:
        """List all URLs tracked by a tenant."""
        pass
    
    @abstractmethod
    async def delete(self, tracking_id: UUID, tenant_id: UUID) -> bool:
        """Delete tracking record."""
        pass


# ============================================================
# Price History Repository (Public Schema)
# ============================================================

class SharedPriceHistoryRepository(ABC):
    """Repository for price history data."""
    
    @abstractmethod
    async def create(self, price_record: SharedPriceHistory) -> SharedPriceHistory:
        """Create a new price record."""
        pass
    
    @abstractmethod
    async def bulk_create(self, price_records: List[SharedPriceHistory]) -> List[SharedPriceHistory]:
        """Bulk create price records."""
        pass
    
    @abstractmethod
    async def get_latest_price(self, product_url_id: UUID) -> Optional[SharedPriceHistory]:
        """Get latest price for product URL."""
        pass
    
    @abstractmethod
    async def get_price_history(
        self,
        product_url_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[SharedPriceHistory]:
        """Get price history for product URL."""
        pass
    
    @abstractmethod
    async def get_average_price(
        self,
        product_url_id: UUID,
        days: int = 30
    ) -> Optional[float]:
        """Calculate average price over period."""
        pass
    
    @abstractmethod
    async def get_price_trend(
        self,
        product_url_id: UUID,
        days: int = 30
    ) -> dict:
        """Get price trend statistics (min, max, avg, current)."""
        pass
