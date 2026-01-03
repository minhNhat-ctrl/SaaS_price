"""
Product Service - Business Logic

Orchestrates product management operations.
No Django dependencies - pure business logic.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta

from services.products.domain import (
    TenantProduct,
    SharedProduct,
    SharedProductURL,
    SharedPriceHistory,
    TenantProductURLTracking,
    ProductStatus,
    MarketplaceType,
    PriceSource,
    TenantProductNotFoundError,
    TenantProductAlreadyExistsError,
    SharedProductNotFoundError,
    InvalidPriceError,
)
from services.products.repositories import (
    TenantProductRepository,
    SharedProductRepository,
    SharedProductURLRepository,
    TenantProductURLTrackingRepository,
    SharedPriceHistoryRepository,
)


class ProductService:
    """
    Main service for product operations.
    
    Responsibilities:
    - Manage tenant products
    - Link tenant products to shared products
    - Manage product URLs
    - Track price history
    """
    
    def __init__(
        self,
        tenant_product_repo: TenantProductRepository,
        shared_product_repo: SharedProductRepository,
        product_url_repo: SharedProductURLRepository,
        url_tracking_repo: TenantProductURLTrackingRepository,
        price_history_repo: SharedPriceHistoryRepository,
    ):
        self.tenant_product_repo = tenant_product_repo
        self.shared_product_repo = shared_product_repo
        self.product_url_repo = product_url_repo
        self.url_tracking_repo = url_tracking_repo
        self.price_history_repo = price_history_repo
    
    # ============================================================
    # Tenant Product Management
    # ============================================================
    
    async def create_tenant_product(
        self,
        tenant_id: UUID,
        name: str,
        sku: str = "",
        internal_code: str = "",
        barcode: str = "",
        gtin: str = "",
        brand: str = "",
        category: str = "",
        **kwargs
    ) -> TenantProduct:
        """
        Create new tenant product.
        
        Args:
            tenant_id: Tenant ID
            name: Product name
            sku: SKU code (tenant-specific)
            internal_code: Internal product code
            barcode: Barcode
            gtin: GTIN for linking to shared product
            brand: Brand name
            category: Category
            **kwargs: Additional custom attributes
        
        Returns:
            Created tenant product
        
        Raises:
            TenantProductAlreadyExistsError: If SKU exists
        """
        # Check if SKU already exists
        if sku:
            existing = await self.tenant_product_repo.get_by_sku(sku, tenant_id)
            if existing:
                raise TenantProductAlreadyExistsError(sku, str(tenant_id))
        
        # Create product
        product = TenantProduct(
            id=uuid4(),  # Generate unique ID
            tenant_id=tenant_id,
            name=name,
            sku=sku,
            internal_code=internal_code,
            barcode=barcode,
            gtin=gtin,
            brand=brand,
            category=category,
            custom_attributes=kwargs.get('custom_attributes', {}),
            status=ProductStatus.DRAFT,
        )
        
        return await self.tenant_product_repo.create(product)
    
    async def get_tenant_product(
        self,
        product_id: UUID,
        tenant_id: UUID
    ) -> Optional[TenantProduct]:
        """Get tenant product by ID."""
        return await self.tenant_product_repo.get_by_id(product_id, tenant_id)
    
    async def update_tenant_product(
        self,
        product_id: UUID,
        tenant_id: UUID,
        **update_data
    ) -> TenantProduct:
        """
        Update tenant product information.
        
        Raises:
            TenantProductNotFoundError: If product not found
        """
        product = await self.tenant_product_repo.get_by_id(product_id, tenant_id)
        if not product:
            raise TenantProductNotFoundError(str(product_id), str(tenant_id))
        
        product.update_info(**update_data)
        return await self.tenant_product_repo.update(product)
    
    async def activate_product(
        self,
        product_id: UUID,
        tenant_id: UUID
    ) -> TenantProduct:
        """Activate product."""
        product = await self.tenant_product_repo.get_by_id(product_id, tenant_id)
        if not product:
            raise TenantProductNotFoundError(str(product_id), str(tenant_id))
        
        product.activate()
        return await self.tenant_product_repo.update(product)
    
    async def archive_product(
        self,
        product_id: UUID,
        tenant_id: UUID
    ) -> TenantProduct:
        """Archive product."""
        product = await self.tenant_product_repo.get_by_id(product_id, tenant_id)
        if not product:
            raise TenantProductNotFoundError(str(product_id), str(tenant_id))
        
        product.archive()
        return await self.tenant_product_repo.update(product)
    
    async def delete_tenant_product(
        self,
        product_id: UUID,
        tenant_id: UUID
    ) -> bool:
        """Delete tenant product."""
        return await self.tenant_product_repo.delete(product_id, tenant_id)
    
    async def list_tenant_products(
        self,
        tenant_id: UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TenantProduct]:
        """List products for tenant."""
        return await self.tenant_product_repo.list_by_tenant(
            tenant_id=tenant_id,
            status=status,
            limit=limit,
            offset=offset
        )
    
    async def search_tenant_products(
        self,
        tenant_id: UUID,
        query: str,
        limit: int = 50
    ) -> List[TenantProduct]:
        """Search tenant products."""
        return await self.tenant_product_repo.search(tenant_id, query, limit)
    
    # ============================================================
    # Shared Product Management
    # ============================================================
    
    async def link_to_shared_product(
        self,
        tenant_product_id: UUID,
        tenant_id: UUID,
        gtin: str = "",
        ean: str = "",
        upc: str = "",
        manufacturer: str = "",
        create_if_not_exists: bool = True
    ) -> TenantProduct:
        """
        Link tenant product to shared canonical product.
        
        Args:
            tenant_product_id: Tenant product ID
            tenant_id: Tenant ID
            gtin: GTIN identifier
            ean: EAN identifier
            upc: UPC identifier
            manufacturer: Manufacturer name
            create_if_not_exists: Create shared product if not found
        
        Returns:
            Updated tenant product
        
        Raises:
            TenantProductNotFoundError: If tenant product not found
            SharedProductNotFoundError: If shared product not found and create_if_not_exists=False
        """
        # Get tenant product
        tenant_product = await self.tenant_product_repo.get_by_id(tenant_product_id, tenant_id)
        if not tenant_product:
            raise TenantProductNotFoundError(str(tenant_product_id), str(tenant_id))
        
        # Find or create shared product
        if create_if_not_exists:
            shared_product = await self.shared_product_repo.find_or_create_by_identifiers(
                gtin=gtin or tenant_product.gtin,
                ean=ean,
                upc=upc,
                manufacturer=manufacturer,
                normalized_name=tenant_product.name.lower().strip()
            )
        else:
            shared_product = await self.shared_product_repo.get_by_gtin(gtin or tenant_product.gtin)
            if not shared_product:
                raise SharedProductNotFoundError(gtin)
        
        # Link tenant product to shared product
        tenant_product.link_to_shared_product(shared_product.id)
        return await self.tenant_product_repo.update(tenant_product)
    
    async def get_shared_product(self, product_id: UUID) -> Optional[SharedProduct]:
        """Get shared product by ID."""
        return await self.shared_product_repo.get_by_id(product_id)
    
    async def find_shared_product_by_gtin(self, gtin: str) -> Optional[SharedProduct]:
        """Find shared product by GTIN."""
        return await self.shared_product_repo.get_by_gtin(gtin)
    
    # ============================================================
    # Product URL Management
    # ============================================================
    
    async def add_product_url(
        self,
        product_id: UUID,
        url: str,
        marketplace: Optional[str] = None,
        is_primary: bool = False,
        tenant_id: Optional[UUID] = None,
        **meta
    ) -> SharedProductURL:
        """
        Add URL to product for tracking.
        
        Strategy: Shared URLs are reused across tenants. If URL already exists in shared schema,
        we create a tracking record linking tenant's product to existing shared URL.
        
        Args:
            product_id: TenantProduct ID
            url: Full URL
            marketplace: Marketplace name (e.g., Amazon, eBay)
            is_primary: Whether this is the primary URL for this tenant's product
            tenant_id: Tenant ID
            **meta: Additional metadata
        
        Returns:
            Shared product URL (existing or newly created)
        """
        from uuid import uuid4
        from services.products.infrastructure.django_models import SharedProductURL as SharedProductURLModel
        
        # Step 1: Check if URL already exists in shared schema
        existing_url = await self.product_url_repo.get_by_url(url)
        
        if existing_url:
            # URL exists - Check if tenant is already tracking it
            tracking = await self.url_tracking_repo.get_by_tenant_and_url(
                tenant_id=tenant_id,
                shared_url_id=existing_url.id
            )
            
            if tracking:
                # Tenant already tracking this URL - just return existing URL
                return existing_url
            
            # Create new tracking record (reuse existing shared URL)
            new_tracking = TenantProductURLTracking(
                id=uuid4(),
                tenant_id=tenant_id,
                product_id=product_id,
                shared_url_id=existing_url.id,
                custom_label=meta.get('label', ''),
                is_primary=is_primary,
            )
            await self.url_tracking_repo.create(new_tracking)
            
            return existing_url
        
        # Step 2: URL doesn't exist - Create new shared URL
        url_hash = SharedProductURLModel.hash_url(url) if url else None
        
        product_url = SharedProductURL(
            id=uuid4(),
            product_id=product_id,  # Can be any product_id as reference
            domain=marketplace or "unknown",
            full_url=url,
            url_hash=url_hash,
            marketplace_type=marketplace or "CUSTOM",
            currency="USD",
            is_active=True,
            meta=meta,
        )
        
        created_url = await self.product_url_repo.create(product_url)
        
        # Step 3: Create tracking record for new URL
        new_tracking = TenantProductURLTracking(
            id=uuid4(),
            tenant_id=tenant_id,
            product_id=product_id,
            shared_url_id=created_url.id,
            custom_label=meta.get('label', ''),
            is_primary=is_primary,
        )
        await self.url_tracking_repo.create(new_tracking)
        
        return created_url
    
    async def get_product_urls(
        self,
        product_id: UUID,
        is_active: Optional[bool] = None
    ) -> List[SharedProductURL]:
        """Get all URLs for shared product."""
        return await self.product_url_repo.list_by_product(product_id, is_active)
    
    async def list_product_urls(
        self,
        product_id: UUID,
        tenant_id: Optional[UUID] = None,
        **kwargs
    ) -> List[SharedProductURL]:
        """List all URLs for product (tenant_id is optional for API)."""
        return await self.get_product_urls(product_id)
    
    async def deactivate_product_url(self, url_id: UUID) -> SharedProductURL:
        """Deactivate product URL."""
        product_url = await self.product_url_repo.get_by_id(url_id)
        if product_url:
            product_url.deactivate()
            return await self.product_url_repo.update(product_url)
        return product_url
    
    async def update_product_url(
        self,
        url_id: UUID,
        url: Optional[str] = None,
        marketplace: Optional[str] = None,
        is_primary: Optional[bool] = None,
    ) -> SharedProductURL:
        """
        Update product URL.
        
        Args:
            url_id: Product URL ID
            url: New URL value
            marketplace: New marketplace name
            is_primary: Update primary flag
        
        Returns:
            Updated product URL
        """
        product_url = await self.product_url_repo.get_by_id(url_id)
        if not product_url:
            raise ValueError(f"Product URL {url_id} not found")
        
        if url:
            product_url.full_url = url
        
        if marketplace:
            product_url.domain = marketplace
            product_url.marketplace_type = marketplace
        
        if is_primary is not None:
            product_url.is_active = not is_primary
        
        return await self.product_url_repo.update(product_url)
    
    async def delete_product_url(self, url_id: UUID) -> bool:
        """
        Delete product URL.
        
        Args:
            url_id: Product URL ID
        
        Returns:
            True if deleted, False if not found
        """
        return await self.product_url_repo.delete(url_id)
    
    # ============================================================
    # Price History Management
    # ============================================================
    
    async def record_price(
        self,
        product_url_id: UUID,
        price: float,
        currency: str,
        source: PriceSource = PriceSource.CRAWLER,
        recorded_at: Optional[datetime] = None,
        **meta
    ) -> SharedPriceHistory:
        """
        Record price for product URL.
        
        Args:
            product_url_id: Product URL ID
            price: Price value
            currency: Currency code
            source: Price source
            recorded_at: Timestamp (defaults to now)
            **meta: Additional metadata
        
        Returns:
            Created price record
        
        Raises:
            InvalidPriceError: If price is invalid
        """
        if price < 0:
            raise InvalidPriceError(price)
        
        price_record = SharedPriceHistory(
            id=uuid4(),
            product_url_id=product_url_id,
            price=price,
            currency=currency,
            source=source,
            recorded_at=recorded_at or datetime.utcnow(),
            meta=meta,
        )
        
        return await self.price_history_repo.create(price_record)
    
    async def bulk_record_prices(
        self,
        price_records: List[Dict[str, Any]]
    ) -> List[SharedPriceHistory]:
        """Bulk record prices."""
        records = []
        for data in price_records:
            if data.get('price', 0) < 0:
                continue  # Skip invalid prices
            
            record = SharedPriceHistory(
                id=uuid4(),
                product_url_id=data['product_url_id'],
                price=data['price'],
                currency=data.get('currency', 'USD'),
                source=data.get('source', PriceSource.CRAWLER),
                recorded_at=data.get('recorded_at', datetime.utcnow()),
                meta=data.get('meta', {}),
            )
            records.append(record)
        
        return await self.price_history_repo.bulk_create(records)
    
    async def get_latest_price(self, product_url_id: UUID) -> Optional[SharedPriceHistory]:
        """Get latest price for product URL."""
        return await self.price_history_repo.get_latest_price(product_url_id)
    
    async def get_price_history(
        self,
        product_url_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[SharedPriceHistory]:
        """Get price history for product URL."""
        return await self.price_history_repo.get_price_history(
            product_url_id=product_url_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    
    async def get_price_statistics(
        self,
        product_url_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get price statistics.
        
        Returns:
            Dict with min, max, avg, current price and trend
        """
        trend = await self.price_history_repo.get_price_trend(product_url_id, days)
        latest = await self.price_history_repo.get_latest_price(product_url_id)
        
        return {
            'trend': trend,
            'current_price': latest.price if latest else None,
            'currency': latest.currency if latest else None,
            'last_updated': latest.recorded_at if latest else None,
        }
