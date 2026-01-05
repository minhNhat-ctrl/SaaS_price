"""
Product Domain Exceptions (Tenant)

Business exceptions for tenant-owned data.
No framework dependencies.
"""


class ProductDomainError(Exception):
    """Base exception for product domain."""
    pass


# ============================================================
# Product Exceptions
# ============================================================

class ProductNotFoundError(ProductDomainError):
    """Product not found."""
    
    def __init__(self, product_id: str, tenant_id: str = ""):
        self.product_id = product_id
        self.tenant_id = tenant_id
        msg = f"Product {product_id} not found"
        if tenant_id:
            msg += f" for tenant {tenant_id}"
        super().__init__(msg)


class DuplicateSKUError(ProductDomainError):
    """SKU already exists for this tenant."""
    
    def __init__(self, sku: str, tenant_id: str = ""):
        self.sku = sku
        self.tenant_id = tenant_id
        super().__init__(f"SKU '{sku}' already exists for tenant {tenant_id}")


class DuplicateGTINError(ProductDomainError):
    """GTIN already exists for this tenant."""
    
    def __init__(self, gtin: str, tenant_id: str = ""):
        self.gtin = gtin
        self.tenant_id = tenant_id
        super().__init__(f"GTIN '{gtin}' already exists for tenant {tenant_id}")


class InvalidProductStatusError(ProductDomainError):
    """Invalid product status transition."""
    
    def __init__(self, current_status: str, new_status: str):
        self.current_status = current_status
        self.new_status = new_status
        super().__init__(f"Cannot transition from {current_status} to {new_status}")


# ============================================================
# URL Mapping Exceptions
# ============================================================

class URLMappingNotFoundError(ProductDomainError):
    """URL mapping not found."""
    
    def __init__(self, url_hash: str, product_id: str = ""):
        self.url_hash = url_hash
        self.product_id = product_id
        msg = f"URL mapping for hash {url_hash[:16]}... not found"
        if product_id:
            msg += f" in product {product_id}"
        super().__init__(msg)


class DuplicateURLError(ProductDomainError):
    """URL already exists for this tenant."""
    
    def __init__(self, url: str, tenant_id: str = ""):
        self.url = url
        self.tenant_id = tenant_id
        super().__init__(
            f"URL '{url}' already exists for tenant {tenant_id}. "
            "A tenant cannot add the same URL to multiple products."
        )


class InvalidURLError(ProductDomainError):
    """Invalid URL format."""
    
    def __init__(self, url: str, reason: str = ""):
        self.url = url
        self.reason = reason
        msg = f"Invalid URL: {url}"
        if reason:
            msg += f" - {reason}"
        super().__init__(msg)
