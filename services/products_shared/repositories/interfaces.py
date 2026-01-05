"""
Shared Repository Interfaces

Abstract interfaces for shared data access.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from services.products_shared.domain.entities import Domain, ProductURL, PriceHistory


class DomainRepository(ABC):
    """Repository interface for Domain."""
    
    @abstractmethod
    def get_by_id(self, domain_id: UUID) -> Optional[Domain]:
        """Get domain by ID."""
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Domain]:
        """Get domain by name."""
        pass
    
    @abstractmethod
    def get_or_create(self, name: str) -> Domain:
        """Get existing domain or create new one."""
        pass
    
    @abstractmethod
    def list_active(self) -> List[Domain]:
        """List all active domains."""
        pass
    
    @abstractmethod
    def update(self, domain: Domain) -> Domain:
        """Update domain."""
        pass


class ProductURLRepository(ABC):
    """Repository interface for ProductURL."""
    
    @abstractmethod
    def get_by_id(self, url_id: UUID) -> Optional[ProductURL]:
        """Get URL by ID."""
        pass
    
    @abstractmethod
    def get_by_hash(self, url_hash: str) -> Optional[ProductURL]:
        """Get URL by hash."""
        pass
    
    @abstractmethod
    def create(self, product_url: ProductURL) -> ProductURL:
        """Create new ProductURL."""
        pass
    
    @abstractmethod
    def increment_reference(self, url_hash: str) -> bool:
        """Increment reference count. Returns True if successful."""
        pass
    
    @abstractmethod
    def decrement_reference(self, url_hash: str) -> int:
        """Decrement reference count. Returns new count."""
        pass
    
    @abstractmethod
    def delete_if_orphaned(self, url_hash: str) -> bool:
        """Delete URL if reference_count is 0. Returns True if deleted."""
        pass
    
    @abstractmethod
    def list_for_crawling(self, limit: int = 100) -> List[ProductURL]:
        """List URLs ready for crawling."""
        pass
    
    @abstractmethod
    def update_crawl_status(
        self,
        url_hash: str,
        success: bool,
        error: str = ""
    ) -> bool:
        """Update crawl status."""
        pass


class PriceHistoryRepository(ABC):
    """Repository interface for PriceHistory."""
    
    @abstractmethod
    def create(self, price_history: PriceHistory) -> PriceHistory:
        """Create new price history record."""
        pass
    
    @abstractmethod
    def get_latest_by_url(self, product_url_id: UUID) -> Optional[PriceHistory]:
        """Get latest price for a URL."""
        pass
    
    @abstractmethod
    def get_latest_by_hash(self, url_hash: str) -> Optional[PriceHistory]:
        """Get latest price for a URL by hash."""
        pass
    
    @abstractmethod
    def list_by_url(
        self,
        product_url_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[PriceHistory]:
        """List price history for a URL."""
        pass
    
    @abstractmethod
    def list_by_hash(
        self,
        url_hash: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[PriceHistory]:
        """List price history for a URL by hash."""
        pass
    
    @abstractmethod
    def get_price_trend(
        self,
        url_hash: str,
        days: int = 30
    ) -> List[PriceHistory]:
        """Get price trend for last N days."""
        pass
    
    @abstractmethod
    def delete_by_url(self, product_url_id: UUID) -> int:
        """Delete all price history for a URL. Returns count deleted."""
        pass
