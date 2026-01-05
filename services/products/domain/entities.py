"""
Product Domain Entities (Tenant Data)

Pure business logic - no framework dependencies.
These entities are for TENANT schema data only.

For shared entities (Domain, ProductURL, PriceHistory), 
see services.products_shared.domain.entities
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from enum import Enum


class ProductStatus(str, Enum):
    """Product status."""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DRAFT = "DRAFT"
    DISCONTINUED = "DISCONTINUED"


# ============================================================
# Tenant Product Entity
# ============================================================

@dataclass
class Product:
    """
    Tenant Product - Product owned by a specific tenant.
    
    Lives in TENANT schema.
    Full CRUD by tenant owner.
    SKU and GTIN must be unique per tenant.
    """
    id: UUID
    tenant_id: UUID
    
    # Product Identifiers
    name: str
    sku: str = ""
    gtin: str = ""
    internal_code: str = ""
    barcode: str = ""
    qr_code: str = ""
    
    # Product Info
    brand: str = ""
    category: str = ""
    description: str = ""
    
    # Status
    status: ProductStatus = ProductStatus.DRAFT
    is_public: bool = False
    
    # Extensibility
    custom_attributes: Dict[str, Any] = field(default_factory=dict)
    
    # Audit
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def activate(self) -> None:
        """Activate product."""
        self.status = ProductStatus.ACTIVE
        self.updated_at = datetime.utcnow()
    
    def archive(self) -> None:
        """Archive product."""
        self.status = ProductStatus.ARCHIVED
        self.updated_at = datetime.utcnow()
    
    def discontinue(self) -> None:
        """Mark product as discontinued."""
        self.status = ProductStatus.DISCONTINUED
        self.updated_at = datetime.utcnow()
    
    def update(self, **kwargs) -> None:
        """Update product fields."""
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                if key == 'status' and isinstance(value, str):
                    # Normalize to uppercase to match enum values
                    setattr(self, key, ProductStatus(value.upper()))
                else:
                    setattr(self, key, value)
        self.updated_at = datetime.utcnow()


# ============================================================
# ProductURLMapping Entity (Ownership)
# ============================================================

@dataclass
class ProductURLMapping:
    """
    Links tenant's Product to shared ProductURL.
    
    Lives in TENANT schema.
    References shared ProductURL via url_hash (cross-schema safe).
    
    A tenant can only add the same URL once (regardless of product).
    """
    id: UUID
    product_id: UUID
    url_hash: str  # SHA-256 hash referencing ProductURL in public schema
    
    # Tenant-specific metadata
    custom_label: str = ""
    is_primary: bool = False
    display_order: int = 0
    
    # Audit
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def set_as_primary(self) -> None:
        """Mark this URL as primary for the product."""
        self.is_primary = True
        self.updated_at = datetime.utcnow()
    
    def unset_as_primary(self) -> None:
        """Unmark this URL as primary."""
        self.is_primary = False
        self.updated_at = datetime.utcnow()
    
    def update_label(self, label: str) -> None:
        """Update custom label."""
        self.custom_label = label
        self.updated_at = datetime.utcnow()
    
    def update_order(self, order: int) -> None:
        """Update display order."""
        self.display_order = order
        self.updated_at = datetime.utcnow()
