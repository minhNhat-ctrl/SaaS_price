"""
Shared Domain Entities

System-governed entities stored in PUBLIC schema.
These are shared across all tenants.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4
import hashlib
from urllib.parse import urlparse


@dataclass
class Domain:
    """
    Domain entity - represents a website domain for crawling.
    
    Stored in PUBLIC schema, managed by system/admin.
    Examples: amazon.co.jp, rakuten.co.jp
    """
    id: UUID
    name: str  # Domain name (e.g., amazon.co.jp)
    
    # Crawl configuration
    crawl_enabled: bool = True
    crawl_interval_hours: int = 24
    rate_limit_per_minute: int = 10
    
    # Parser configuration
    parser_class: str = ""
    parser_config: dict = field(default_factory=dict)
    
    # Status
    is_active: bool = True
    last_health_check: Optional[datetime] = None
    health_status: str = "OK"  # OK, DEGRADED, DOWN
    
    # Audit
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @classmethod
    def create(cls, name: str, **kwargs) -> 'Domain':
        """Factory method to create a new Domain."""
        return cls(
            id=uuid4(),
            name=name.lower().strip(),
            **kwargs
        )
    
    @classmethod
    def extract_from_url(cls, url: str) -> str:
        """Extract domain name from URL."""
        parsed = urlparse(url)
        return parsed.netloc.lower()


@dataclass
class ProductURL:
    """
    ProductURL entity - represents a unique product URL in the system.
    
    Stored in PUBLIC schema, deduplicated by url_hash.
    Shared across all tenants - when one tenant adds a URL that already exists,
    the system reuses the existing ProductURL and increments reference_count.
    """
    id: UUID
    url_hash: str  # SHA-256 of normalized_url - UNIQUE
    
    # URL data
    raw_url: str  # Original URL as entered
    normalized_url: str  # Lowercase, no tracking params
    
    # Domain reference
    domain_id: UUID
    
    # Reference counting
    reference_count: int = 0  # Number of tenant mappings to this URL
    
    # Crawl status
    is_active: bool = True
    last_crawled_at: Optional[datetime] = None
    crawl_error: str = ""
    
    # Audit
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Tracking params to remove during normalization
    TRACKING_PARAMS = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'gclsrc', 'dclid', 'zanpid', 'msclkid',
        'ref', 'ref_', 'referer', 'referrer', 'source', 'src',
        'campaign', 'affiliate', 'aff', 'partner',
        'mc_cid', 'mc_eid', '_ga', '_gl', 'spm'
    }
    
    @classmethod
    def normalize_url(cls, raw_url: str) -> str:
        """
        Normalize URL for consistent hashing.
        - Lowercase
        - Remove tracking parameters
        - Standardize scheme
        """
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        
        # Parse URL
        parsed = urlparse(raw_url.strip())
        
        # Lowercase host and path
        host = parsed.netloc.lower()
        path = parsed.path.lower()
        
        # Remove trailing slash from path (except for root)
        if path != '/' and path.endswith('/'):
            path = path.rstrip('/')
        
        # Filter out tracking params
        query_params = parse_qs(parsed.query, keep_blank_values=False)
        filtered_params = {
            k: v for k, v in query_params.items()
            if k.lower() not in cls.TRACKING_PARAMS
        }
        
        # Sort params for consistency
        sorted_params = sorted(filtered_params.items())
        new_query = urlencode(sorted_params, doseq=True)
        
        # Reconstruct URL
        normalized = urlunparse((
            parsed.scheme.lower() or 'https',
            host,
            path,
            '',  # params
            new_query,
            ''  # fragment
        ))
        
        return normalized
    
    @classmethod
    def generate_hash(cls, normalized_url: str) -> str:
        """Generate SHA-256 hash of normalized URL."""
        return hashlib.sha256(normalized_url.encode('utf-8')).hexdigest()
    
    @classmethod
    def create(cls, raw_url: str, domain_id: UUID) -> 'ProductURL':
        """Factory method to create a new ProductURL."""
        normalized = cls.normalize_url(raw_url)
        url_hash = cls.generate_hash(normalized)
        
        return cls(
            id=uuid4(),
            url_hash=url_hash,
            raw_url=raw_url,
            normalized_url=normalized,
            domain_id=domain_id,
            reference_count=1,  # Start with 1 when created
        )
    
    def increment_reference(self) -> None:
        """Increment reference count when a tenant adds this URL."""
        self.reference_count += 1
        self.updated_at = datetime.utcnow()
    
    def decrement_reference(self) -> None:
        """Decrement reference count when a tenant removes this URL."""
        if self.reference_count > 0:
            self.reference_count -= 1
        self.updated_at = datetime.utcnow()
    
    def is_orphaned(self) -> bool:
        """Check if URL has no references and can be deleted."""
        return self.reference_count <= 0
    
    def mark_crawl_success(self) -> None:
        """Mark successful crawl."""
        self.last_crawled_at = datetime.utcnow()
        self.crawl_error = ""
        self.updated_at = datetime.utcnow()
    
    def mark_crawl_error(self, error: str) -> None:
        """Mark crawl error."""
        self.crawl_error = error
        self.updated_at = datetime.utcnow()


@dataclass
class PriceHistory:
    """
    PriceHistory entity - records price at a point in time.
    
    Stored in PUBLIC schema, linked to ProductURL.
    Append-only - no updates or deletes.
    Shared across all tenants using the same ProductURL.
    """
    id: UUID
    product_url_id: UUID  # FK → ProductURL
    
    # Price data
    price: Decimal
    currency: str = "JPY"
    original_price: Optional[Decimal] = None  # List/regular price before discount
    
    # Availability
    is_available: bool = True
    stock_status: str = ""  # IN_STOCK, OUT_OF_STOCK, LIMITED, PREORDER
    stock_quantity: Optional[int] = None
    
    # Source
    source: str = "CRAWLER"  # CRAWLER, API, MANUAL, IMPORT
    
    # Timing
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @classmethod
    def create(
        cls,
        product_url_id: UUID,
        price: Decimal,
        currency: str = "JPY",
        source: str = "CRAWLER",
        **kwargs
    ) -> 'PriceHistory':
        """Factory method to create a new PriceHistory record."""
        return cls(
            id=uuid4(),
            product_url_id=product_url_id,
            price=price,
            currency=currency,
            source=source,
            **kwargs
        )
    
    def calculate_discount_percentage(self) -> Optional[float]:
        """Calculate discount percentage if original_price is set."""
        if self.original_price and self.original_price > 0:
            discount = (self.original_price - self.price) / self.original_price * 100
            return round(float(discount), 2)
        return None
    
    def has_discount(self) -> bool:
        """Check if item is discounted."""
        return self.original_price is not None and self.price < self.original_price
