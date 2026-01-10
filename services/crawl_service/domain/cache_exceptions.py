"""
Domain Layer - Cache Exceptions

Pure domain exceptions for cache operations.
Framework-agnostic.
"""


class CacheException(Exception):
    """Base exception for cache operations"""
    pass


class CacheConnectionError(CacheException):
    """Cache connection failed"""
    pass


class CacheOperationError(CacheException):
    """Cache operation (get/set/delete) failed"""
    pass


class CacheConfigurationError(CacheException):
    """Cache is not properly configured"""
    pass


class CacheKeyError(CacheException):
    """Invalid cache key"""
    pass
