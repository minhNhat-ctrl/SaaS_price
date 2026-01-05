"""
Product Use Cases

Application service layer - Orchestrates domain logic and repository operations.
Implements business use cases according to PRODUCTS_DATA_CONTRACT.md

Architecture:
- Product, ProductURLMapping: Tenant schema (services.products)
- Domain, ProductURL, PriceHistory: Public schema (services.products_shared)
"""
from typing import Optional, List, Tuple
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass

from services.products.domain import (
    Product,
    ProductURLMapping,
    ProductStatus,
    DuplicateSKUError,
    DuplicateGTINError,
    DuplicateURLError,
    ProductNotFoundError,
    URLMappingNotFoundError,
    InvalidURLError,
)
from services.products.repositories import (
    ProductRepository,
    ProductURLMappingRepository,
)

# Import from shared module for public schema data
from services.products_shared.domain import (
    Domain,
    ProductURL,
    PriceHistory,
    URLNotFoundError,
)
from services.products_shared.repositories import (
    DomainRepository,
    ProductURLRepository,
    PriceHistoryRepository,
)


# ============================================================
# DTOs for Cross-Schema Responses
# ============================================================

@dataclass
class ProductURLInfo:
    """Combined info from tenant mapping and shared URL."""
    mapping: ProductURLMapping
    url: ProductURL
    latest_price: Optional[PriceHistory] = None


# ============================================================
# Product Service (Tenant Operations)
# ============================================================

class ProductService:
    """
    Service for managing products.
    
    Coordinates between tenant and shared repositories.
    """
    
    def __init__(
        self,
        product_repo: ProductRepository,
        mapping_repo: ProductURLMappingRepository,
        url_repo: ProductURLRepository,
        domain_repo: DomainRepository = None,
    ):
        self.product_repo = product_repo
        self.mapping_repo = mapping_repo
        self.url_repo = url_repo  # Shared (public schema)
        self.domain_repo = domain_repo  # Shared (public schema)
    
    def create_product(
        self,
        tenant_id: UUID,
        name: str,
        sku: str = "",
        gtin: str = "",
        **kwargs
    ) -> Product:
        """
        Create a new product for tenant.
        
        Validates:
        - SKU must be unique per tenant (if provided)
        - GTIN must be unique per tenant (if provided)
        """
        # Validate SKU uniqueness
        if sku and self.product_repo.exists_by_sku(sku, tenant_id):
            raise DuplicateSKUError(sku, str(tenant_id))
        
        # Validate GTIN uniqueness
        if gtin and self.product_repo.exists_by_gtin(gtin, tenant_id):
            raise DuplicateGTINError(gtin, str(tenant_id))
        
        # Parse status
        status_value = kwargs.get('status', 'active')
        if isinstance(status_value, str):
            try:
                status = ProductStatus(status_value.lower())
            except ValueError:
                status = ProductStatus.ACTIVE
        else:
            status = status_value
        
        # Create product entity
        product = Product(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            sku=sku,
            gtin=gtin,
            status=status,
            custom_attributes=kwargs.get('custom_attributes', {}),
        )
        
        # Persist to repository
        return self.product_repo.create(product)
    
    def update_product(
        self,
        product_id: UUID,
        tenant_id: UUID,
        **updates
    ) -> Product:
        """Update product information."""
        # Get existing product
        product = self.product_repo.get_by_id(product_id, tenant_id)
        if not product:
            raise ProductNotFoundError(str(product_id), str(tenant_id))
        
        # Validate SKU uniqueness if changing
        if 'sku' in updates and updates['sku'] and updates['sku'] != product.sku:
            if self.product_repo.exists_by_sku(updates['sku'], tenant_id):
                raise DuplicateSKUError(updates['sku'], str(tenant_id))
        
        # Validate GTIN uniqueness if changing
        if 'gtin' in updates and updates['gtin'] and updates['gtin'] != product.gtin:
            if self.product_repo.exists_by_gtin(updates['gtin'], tenant_id):
                raise DuplicateGTINError(updates['gtin'], str(tenant_id))
        
        # Update product using domain method
        product.update(**updates)
        
        return self.product_repo.update(product)
    
    def get_product(self, product_id: UUID, tenant_id: UUID) -> Optional[Product]:
        """Get product by ID."""
        return self.product_repo.get_by_id(product_id, tenant_id)
    
    def list_products(
        self,
        tenant_id: UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Product]:
        """List products for tenant."""
        return self.product_repo.list_by_tenant(tenant_id, status, limit, offset)
    
    def delete_product(self, product_id: UUID, tenant_id: UUID) -> bool:
        """
        Delete product and clean up URL references.
        
        Process:
        1. Get all URL mappings for this product
        2. For each mapping, decrement reference count in shared ProductURL
        3. Delete product (cascades to mappings)
        """
        # Get all URL mappings for this product
        self.mapping_repo.set_tenant(tenant_id)
        mappings = self.mapping_repo.list_by_product(product_id)
        
        # Decrement reference count for each URL
        for mapping in mappings:
            self.url_repo.decrement_reference(mapping.url_hash)
        
        # Delete the product (cascades to mappings via FK)
        return self.product_repo.delete(product_id, tenant_id)
    
    def add_url_to_product(
        self,
        tenant_id: UUID,
        product_id: UUID,
        raw_url: str,
        custom_label: str = "",
        is_primary: bool = False,
    ) -> ProductURLInfo:
        """
        Add URL to product.
        
        Process:
        1. Validate product exists
        2. Extract domain from URL and get/create Domain entity
        3. Create ProductURL entity with domain_id
        4. Check if URL already exists in shared (by hash)
        5. Check if tenant already has this URL mapped (prevent duplicate)
        6. If URL doesn't exist in shared, create it
        7. Create mapping in tenant schema
        8. Increment reference count in shared
        """
        # Validate product exists
        product = self.product_repo.get_by_id(product_id, tenant_id)
        if not product:
            raise ProductNotFoundError(str(product_id), str(tenant_id))
        
        # Extract domain from URL and get/create Domain entity
        domain_name = Domain.extract_from_url(raw_url)
        if not domain_name:
            raise InvalidURLError(raw_url, "Could not extract domain from URL")
        
        # Get or create Domain in shared (public schema)
        domain = self.domain_repo.get_or_create(domain_name)
        
        # Create ProductURL entity (generates hash and domain automatically)
        try:
            product_url = ProductURL.create(raw_url, domain.id)
        except Exception as e:
            raise InvalidURLError(raw_url, str(e))
        
        url_hash = product_url.url_hash
        
        # Check if tenant already has this URL mapped
        self.mapping_repo.set_tenant(tenant_id)
        if self.mapping_repo.exists_for_tenant(tenant_id, url_hash):
            raise DuplicateURLError(raw_url, str(tenant_id))
        
        # Check if URL already exists in shared (public schema)
        existing_url = self.url_repo.get_by_hash(url_hash)
        
        if existing_url:
            # Reuse existing URL
            product_url = existing_url
        else:
            # Create new URL in shared (public schema)
            product_url = self.url_repo.create(product_url)
        
        # Create mapping in tenant schema
        mapping = ProductURLMapping(
            id=uuid4(),
            product_id=product_id,
            url_hash=url_hash,
            custom_label=custom_label,
            is_primary=is_primary,
            display_order=0,
        )
        mapping = self.mapping_repo.create(mapping)
        
        # Increment reference count in shared
        self.url_repo.increment_reference(url_hash)
        
        return ProductURLInfo(mapping=mapping, url=product_url)
    
    def remove_url_from_product(
        self,
        tenant_id: UUID,
        product_id: UUID,
        url_hash: str,
    ) -> bool:
        """
        Remove URL from product.
        
        Process:
        1. Find mapping by product and url_hash
        2. Delete mapping
        3. Decrement URL reference count
        4. If reference count = 0, URL becomes orphaned (cleanup later)
        """
        # Get mapping
        self.mapping_repo.set_tenant(tenant_id)
        mapping = self.mapping_repo.get_by_product_and_hash(product_id, url_hash)
        
        if not mapping:
            raise URLMappingNotFoundError(url_hash, str(product_id))
        
        # Delete mapping
        if not self.mapping_repo.delete(mapping.id):
            return False
        
        # Decrement reference count
        self.url_repo.decrement_reference(url_hash)
        
        return True
    
    def get_product_urls(
        self,
        tenant_id: UUID,
        product_id: UUID
    ) -> List[ProductURLInfo]:
        """
        Get all URLs for a product with their details.
        
        Joins tenant mapping with shared URL data.
        """
        self.mapping_repo.set_tenant(tenant_id)
        mappings = self.mapping_repo.list_by_product(product_id)
        
        result = []
        for mapping in mappings:
            url = self.url_repo.get_by_hash(mapping.url_hash)
            if url:
                result.append(ProductURLInfo(mapping=mapping, url=url))
        
        return result
    
    def search_products(
        self,
        tenant_id: UUID,
        query: str,
        limit: int = 50
    ) -> List[Product]:
        """Search products by name, SKU, or GTIN."""
        return self.product_repo.search(tenant_id, query, limit)
    
    def count_products(self, tenant_id: UUID) -> int:
        """Count products for tenant."""
        return self.product_repo.count_by_tenant(tenant_id)


# ============================================================
# Price Service (Shared Data Operations)
# ============================================================

class PriceService:
    """
    Service for managing price history.
    
    Operates on shared data (public schema).
    """
    
    def __init__(
        self,
        price_history_repo: PriceHistoryRepository,
        url_repo: ProductURLRepository,
    ):
        self.price_history_repo = price_history_repo
        self.url_repo = url_repo
    
    def add_price_record(
        self,
        url_hash: str,
        price: float,
        currency: str = "JPY",
        **kwargs
    ) -> PriceHistory:
        """
        Add price history record.
        
        Uses url_hash to identify the URL.
        """
        # Validate URL exists
        url = self.url_repo.get_by_hash(url_hash)
        if not url:
            raise URLNotFoundError(url_hash)
        
        price_history = PriceHistory(
            id=uuid4(),
            url_hash=url_hash,
            price=price,
            currency=currency,
            original_price=kwargs.get('original_price'),
            source=kwargs.get('source', 'crawler'),
            is_available=kwargs.get('is_available', True),
            stock_status=kwargs.get('stock_status', ''),
            scraped_at=kwargs.get('scraped_at', datetime.utcnow()),
        )
        
        return self.price_history_repo.create(price_history)
    
    def get_latest_price(self, url_hash: str) -> Optional[PriceHistory]:
        """Get latest price for a URL."""
        return self.price_history_repo.get_latest_by_hash(url_hash)
    
    def get_price_history(
        self,
        url_hash: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[PriceHistory]:
        """Get price history for a URL."""
        return self.price_history_repo.list_by_hash(
            url_hash, start_date, end_date, limit
        )
    
    def get_price_trend(
        self,
        url_hash: str,
        days: int = 30
    ) -> List[PriceHistory]:
        """Get price trend for specified number of days."""
        return self.price_history_repo.get_price_trend(url_hash, days)


# ============================================================
# URL Cleanup Service (Shared Data Maintenance)
# ============================================================

class URLCleanupService:
    """
    Service for cleaning up orphaned URLs.
    
    Operates on shared data (public schema).
    """
    
    def __init__(
        self,
        url_repo: ProductURLRepository,
    ):
        self.url_repo = url_repo
    
    def cleanup_orphaned_urls(self, limit: int = 100) -> int:
        """
        Delete URLs with zero references.
        
        Returns number of URLs deleted.
        """
        orphaned_urls = self.url_repo.get_orphaned_urls(limit)
        
        deleted_count = 0
        for url in orphaned_urls:
            if self.url_repo.delete(url.id):
                deleted_count += 1
        
        return deleted_count
