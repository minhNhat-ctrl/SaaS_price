"""
Product Domain Entities

Pure business logic - no framework dependencies.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from enum import Enum


class ProductStatus(str, Enum):
    """Product status."""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DRAFT = "DRAFT"
    DISCONTINUED = "DISCONTINUED"


class MarketplaceType(str, Enum):
    """Marketplace types."""
    AMAZON = "AMAZON"
    RAKUTEN = "RAKUTEN"
    SHOPEE = "SHOPEE"
    LAZADA = "LAZADA"
    MANUFACTURER = "MANUFACTURER"
    CUSTOM = "CUSTOM"


class PriceSource(str, Enum):
    """Price data source."""
    CRAWLER = "CRAWLER"
    API = "API"
    MANUAL = "MANUAL"
    IMPORT = "IMPORT"


# ============================================================
# Tenant-owned Entity (Tenant Schema)
# ============================================================

@dataclass
class TenantProduct:
    """
    Tenant Product - Product managed by specific tenant.
    
    Lives in tenant schema. Each tenant has their own product definitions.
    """
    id: UUID
    tenant_id: UUID
    
    # Basic Info
    name: str
    internal_code: str = ""
    sku: str = ""
    barcode: str = ""
    qr_code: str = ""
    gtin: str = ""
    
    # References
    brand: str = ""
    category: str = ""
    
    # Status
    status: ProductStatus = ProductStatus.DRAFT
    
    # Link to canonical product (shared)
    shared_product_id: Optional[UUID] = None
    
    # Metadata
    custom_attributes: Dict[str, Any] = field(default_factory=dict)
    is_public: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def activate(self):
        """Activate product."""
        self.status = ProductStatus.ACTIVE
        self.updated_at = datetime.utcnow()
    
    def archive(self):
        """Archive product."""
        self.status = ProductStatus.ARCHIVED
        self.updated_at = datetime.utcnow()
    
    def update_info(
        self,
        name: Optional[str] = None,
        internal_code: Optional[str] = None,
        sku: Optional[str] = None,
        barcode: Optional[str] = None,
        brand: Optional[str] = None,
        category: Optional[str] = None,
    ):
        """Update product information."""
        if name is not None:
            self.name = name
        if internal_code is not None:
            self.internal_code = internal_code
        if sku is not None:
            self.sku = sku
        if barcode is not None:
            self.barcode = barcode
        if brand is not None:
            self.brand = brand
        if category is not None:
            self.category = category
        
        self.updated_at = datetime.utcnow()
    
    def link_to_shared_product(self, shared_product_id: UUID):
        """Link to canonical shared product."""
        self.shared_product_id = shared_product_id
        self.updated_at = datetime.utcnow()


# ============================================================
# Shared Entities (Public Schema)
# ============================================================

@dataclass
class SharedProduct:
    """
    Canonical Product - Normalized product across all tenants.
    
    Lives in public schema. Represents the physical/standard product.
    Multiple TenantProducts can map to one SharedProduct.
    """
    id: UUID
    
    # Standard identifiers
    gtin: str = ""  # Global Trade Item Number
    ean: str = ""
    upc: str = ""
    
    # Normalized info
    manufacturer: str = ""
    normalized_name: str = ""
    
    # Specs hash for deduplication
    specs_hash: str = ""
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def update_identifiers(
        self,
        gtin: Optional[str] = None,
        ean: Optional[str] = None,
        upc: Optional[str] = None,
    ):
        """Update product identifiers."""
        if gtin is not None:
            self.gtin = gtin
        if ean is not None:
            self.ean = ean
        if upc is not None:
            self.upc = upc
        
        self.updated_at = datetime.utcnow()


@dataclass
class SharedProductURL:
    """
    Product URL - Marketplace/website URLs for shared products.
    
    Lives in public schema. One SharedProduct can have many URLs
    across different marketplaces.
    """
    id: UUID
    product_id: UUID  # Reference to SharedProduct
    
    # URL Info
    domain: str
    full_url: str
    marketplace_type: MarketplaceType
    
    # Price info
    currency: str = "USD"
    
    # Status
    is_active: bool = True
    
    # Metadata
    meta: Dict[str, Any] = field(default_factory=dict)  # region, seller, variant, etc.
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def deactivate(self):
        """Deactivate URL."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def activate(self):
        """Activate URL."""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    def update_meta(self, **kwargs):
        """Update metadata."""
        self.meta.update(kwargs)
        self.updated_at = datetime.utcnow()


@dataclass
class SharedPriceHistory:
    """
    Price History - Time-series price data.
    
    Lives in public schema. Large volume, read-only data.
    Can use TimescaleDB for partitioning.
    """
    id: UUID
    product_url_id: UUID  # Reference to SharedProductURL
    
    # Price data
    price: float
    currency: str
    
    # Timestamp
    recorded_at: datetime
    
    # Source
    source: PriceSource = PriceSource.CRAWLER
    
    # Optional metadata
    meta: Dict[str, Any] = field(default_factory=dict)  # discount, availability, etc.
    
    def __post_init__(self):
        """Ensure recorded_at is set."""
        if self.recorded_at is None:
            self.recorded_at = datetime.utcnow()
