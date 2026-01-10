"""
Domain Layer - Cache Service Interface

Pure business logic interface for caching crawl jobs and results.
Framework-agnostic - no Django imports.

Cache Strategy:
1. Cache PENDING jobs list by domain/priority (reduce DB queries for /pull/)
2. Cache job details by job_id (reduce lookups in /submit/)
3. Cache ProductURL data (reduce joins)
4. TTL-based expiration aligned with job lifecycle
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime


class ICacheService(ABC):
    """
    Cache service interface for crawl operations.
    
    Implementations must handle:
    - Connection management
    - Serialization/deserialization
    - TTL management
    - Error handling
    """
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache by key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
            
        Raises:
            CacheOperationError: If cache operation fails
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """
        Set value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be serialized)
            ttl_seconds: Time-to-live in seconds (None = use default)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            CacheOperationError: If cache operation fails
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key existed and was deleted, False otherwise
            
        Raises:
            CacheOperationError: If cache operation fails
        """
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
            
        Raises:
            CacheOperationError: If cache operation fails
        """
        pass
    
    @abstractmethod
    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.
        
        Args:
            pattern: Redis pattern (e.g., 'crawl:jobs:*')
            
        Returns:
            Number of keys deleted
            
        Raises:
            CacheOperationError: If cache operation fails
        """
        pass
    
    @abstractmethod
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values at once.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dict mapping keys to values (missing keys excluded)
            
        Raises:
            CacheOperationError: If cache operation fails
        """
        pass
    
    @abstractmethod
    def set_many(self, mapping: Dict[str, Any], ttl_seconds: Optional[int] = None) -> bool:
        """
        Set multiple key-value pairs at once.
        
        Args:
            mapping: Dict of key-value pairs
            ttl_seconds: TTL for all keys (None = use default)
            
        Returns:
            True if all successful, False otherwise
            
        Raises:
            CacheOperationError: If cache operation fails
        """
        pass
    
    @abstractmethod
    def increment(self, key: str, delta: int = 1) -> int:
        """
        Increment counter by delta.
        
        Args:
            key: Cache key
            delta: Amount to increment
            
        Returns:
            New value after increment
            
        Raises:
            CacheOperationError: If cache operation fails
        """
        pass
    
    @abstractmethod
    def ping(self) -> bool:
        """
        Test cache connection.
        
        Returns:
            True if cache is reachable, False otherwise
        """
        pass


class CacheKeyBuilder:
    """
    Pure domain logic for building cache keys.
    
    Consistent key naming prevents collisions and enables pattern-based clearing.
    """
    
    PREFIX = "crawl_service"
    
    @staticmethod
    def pending_jobs(domain: Optional[str] = None, priority: Optional[int] = None) -> str:
        """
        Cache key for pending jobs list.
        
        Examples:
            crawl_service:jobs:pending:all
            crawl_service:jobs:pending:domain:amazon.co.jp
            crawl_service:jobs:pending:priority:10
        """
        if domain:
            return f"{CacheKeyBuilder.PREFIX}:jobs:pending:domain:{domain}"
        elif priority is not None:
            return f"{CacheKeyBuilder.PREFIX}:jobs:pending:priority:{priority}"
        else:
            return f"{CacheKeyBuilder.PREFIX}:jobs:pending:all"
    
    @staticmethod
    def job_detail(job_id: str) -> str:
        """
        Cache key for individual job details.
        
        Example: crawl_service:job:uuid-here
        """
        return f"{CacheKeyBuilder.PREFIX}:job:{job_id}"
    
    @staticmethod
    def product_url(url_hash: str) -> str:
        """
        Cache key for ProductURL data.
        
        Example: crawl_service:url:hash-here
        """
        return f"{CacheKeyBuilder.PREFIX}:url:{url_hash}"
    
    @staticmethod
    def bot_stats(bot_id: str) -> str:
        """
        Cache key for bot statistics.
        
        Example: crawl_service:bot:bot-001:stats
        """
        return f"{CacheKeyBuilder.PREFIX}:bot:{bot_id}:stats"
    
    @staticmethod
    def policy_jobs(policy_id: str) -> str:
        """
        Cache key for jobs belonging to a policy.
        
        Example: crawl_service:policy:uuid:jobs
        """
        return f"{CacheKeyBuilder.PREFIX}:policy:{policy_id}:jobs"
    
    @staticmethod
    def all_jobs_pattern() -> str:
        """Pattern to clear all job caches"""
        return f"{CacheKeyBuilder.PREFIX}:jobs:*"
    
    @staticmethod
    def all_urls_pattern() -> str:
        """Pattern to clear all URL caches"""
        return f"{CacheKeyBuilder.PREFIX}:url:*"
