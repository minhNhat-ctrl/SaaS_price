"""
Shared Domain Exceptions

Exceptions for shared data operations.
"""


class SharedDomainError(Exception):
    """Base exception for shared domain errors."""
    pass


class DomainNotFoundError(SharedDomainError):
    """Domain not found."""
    def __init__(self, domain_name: str):
        self.domain_name = domain_name
        super().__init__(f"Domain '{domain_name}' not found")


class ProductURLNotFoundError(SharedDomainError):
    """ProductURL not found."""
    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"ProductURL '{identifier}' not found")


class ProductURLAlreadyExistsError(SharedDomainError):
    """ProductURL with this hash already exists."""
    def __init__(self, url_hash: str):
        self.url_hash = url_hash
        super().__init__(f"ProductURL with hash '{url_hash}' already exists")


class InvalidURLError(SharedDomainError):
    """Invalid URL format."""
    def __init__(self, url: str, reason: str = ""):
        self.url = url
        self.reason = reason
        message = f"Invalid URL: '{url}'"
        if reason:
            message += f" - {reason}"
        super().__init__(message)


class OrphanedURLError(SharedDomainError):
    """URL has no references and should be deleted."""
    def __init__(self, url_hash: str):
        self.url_hash = url_hash
        super().__init__(f"ProductURL '{url_hash}' is orphaned (reference_count=0)")
