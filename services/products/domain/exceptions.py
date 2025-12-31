"""
Product Domain Exceptions

Business exceptions - no framework dependencies.
"""


class ProductDomainError(Exception):
    """Base exception for product domain."""
    pass


# ============================================================
# Tenant Product Exceptions
# ============================================================

class TenantProductNotFoundError(ProductDomainError):
    """Tenant product not found."""
    
    def __init__(self, product_id: str, tenant_id: str):
        self.product_id = product_id
        self.tenant_id = tenant_id
        super().__init__(f"Tenant product {product_id} not found for tenant {tenant_id}")


class TenantProductAlreadyExistsError(ProductDomainError):
    """Tenant product already exists."""
    
    def __init__(self, sku: str, tenant_id: str):
        self.sku = sku
        self.tenant_id = tenant_id
        super().__init__(f"Product with SKU {sku} already exists for tenant {tenant_id}")


class InvalidProductStatusError(ProductDomainError):
    """Invalid product status transition."""
    
    def __init__(self, current_status: str, new_status: str):
        self.current_status = current_status
        self.new_status = new_status
        super().__init__(f"Cannot transition from {current_status} to {new_status}")


# ============================================================
# Shared Product Exceptions
# ============================================================

class SharedProductNotFoundError(ProductDomainError):
    """Shared product not found."""
    
    def __init__(self, product_id: str):
        self.product_id = product_id
        super().__init__(f"Shared product {product_id} not found")


class SharedProductAlreadyExistsError(ProductDomainError):
    """Shared product already exists."""
    
    def __init__(self, gtin: str):
        self.gtin = gtin
        super().__init__(f"Shared product with GTIN {gtin} already exists")


class DuplicateProductURLError(ProductDomainError):
    """Duplicate product URL."""
    
    def __init__(self, url: str):
        self.url = url
        super().__init__(f"Product URL {url} already exists")


# ============================================================
# Price History Exceptions
# ============================================================

class InvalidPriceError(ProductDomainError):
    """Invalid price value."""
    
    def __init__(self, price: float):
        self.price = price
        super().__init__(f"Invalid price: {price}")


class PriceHistoryNotFoundError(ProductDomainError):
    """Price history not found."""
    
    def __init__(self, product_url_id: str):
        self.product_url_id = product_url_id
        super().__init__(f"No price history found for product URL {product_url_id}")
