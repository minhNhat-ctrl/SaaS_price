"""
Infrastructure Layer - Redis Cache Adapter

Concrete implementation of ICacheService using Redis.
This layer is allowed to import Django and external libraries.

Configuration is loaded from CrawlCacheConfig model (admin-configurable).
"""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

import redis
from django.core.cache import cache as django_cache
from django.conf import settings

from ..domain.cache_service import ICacheService, CacheKeyBuilder
from ..domain.cache_exceptions import (
    CacheConnectionError,
    CacheOperationError,
    CacheConfigurationError
)

logger = logging.getLogger(__name__)


class RedisAdapter(ICacheService):
    """
    Redis implementation of cache service.
    
    Features:
    - Direct Redis connection (not Django cache) for better control
    - JSON serialization for complex objects
    - Configurable via CrawlCacheConfig model
    - Fallback to disabled mode if Redis unavailable
    """
    
    def __init__(self, config=None):
        """
        Initialize Redis adapter.
        
        Args:
            config: CrawlCacheConfig instance or None (will load from DB)
        """
        self._client = None
        self._enabled = False
        self._default_ttl = 300  # 5 minutes default
        
        if config:
            self._configure_from_model(config)
        else:
            self._load_config_from_db()
    
    def _load_config_from_db(self):
        """Load configuration from database (CrawlCacheConfig model)"""
        try:
            # Avoid circular import
            from ..models import CrawlCacheConfig
            
            config = CrawlCacheConfig.get_active_config()
            if config:
                self._configure_from_model(config)
            else:
                logger.warning("No active cache configuration found. Cache disabled.")
                self._enabled = False
        except Exception as e:
            logger.error(f"Failed to load cache config from DB: {e}")
            self._enabled = False
    
    def _configure_from_model(self, config):
        """
        Configure Redis from CrawlCacheConfig model.
        
        Args:
            config: CrawlCacheConfig instance
        """
        try:
            if not config.enabled:
                self._enabled = False
                logger.info("Cache is disabled in configuration")
                return
            
            # Connect to Redis
            self._client = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                db=config.redis_db,
                password=config.redis_password if config.redis_password else None,
                decode_responses=True,  # Auto-decode bytes to strings
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            
            # Test connection
            self._client.ping()
            
            self._enabled = True
            self._default_ttl = config.default_ttl_seconds
            
            logger.info(
                f"Redis cache connected: {config.redis_host}:{config.redis_port} "
                f"DB={config.redis_db}, TTL={self._default_ttl}s"
            )
            
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            raise CacheConnectionError(f"Cannot connect to Redis: {e}")
        except Exception as e:
            logger.error(f"Redis configuration error: {e}")
            raise CacheConfigurationError(f"Invalid cache configuration: {e}")
    
    def _ensure_enabled(self):
        """Check if cache is enabled, raise if not"""
        if not self._enabled or not self._client:
            raise CacheConfigurationError("Cache is not enabled or not configured")
    
    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string"""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps(value)
        elif isinstance(value, datetime):
            return json.dumps(value.isoformat())
        else:
            return json.dumps(value, default=str)
    
    def _deserialize(self, value: Optional[str]) -> Optional[Any]:
        """Deserialize JSON string to value"""
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # Return as-is if not JSON
            return value
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self._enabled:
            return None
        
        try:
            self._ensure_enabled()
            value = self._client.get(key)
            return self._deserialize(value)
        except CacheConfigurationError:
            return None  # Cache disabled, return None
        except redis.RedisError as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            raise CacheOperationError(f"Cache get failed: {e}")
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value in Redis cache with TTL"""
        if not self._enabled:
            return False
        
        try:
            self._ensure_enabled()
            ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
            serialized = self._serialize(value)
            self._client.setex(key, ttl, serialized)
            return True
        except CacheConfigurationError:
            return False  # Cache disabled
        except redis.RedisError as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            raise CacheOperationError(f"Cache set failed: {e}")
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self._enabled:
            return False
        
        try:
            self._ensure_enabled()
            result = self._client.delete(key)
            return result > 0
        except CacheConfigurationError:
            return False
        except redis.RedisError as e:
            logger.error(f"Redis DELETE error for key '{key}': {e}")
            raise CacheOperationError(f"Cache delete failed: {e}")
    
    def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if not self._enabled:
            return False
        
        try:
            self._ensure_enabled()
            return self._client.exists(key) > 0
        except CacheConfigurationError:
            return False
        except redis.RedisError as e:
            logger.error(f"Redis EXISTS error for key '{key}': {e}")
            raise CacheOperationError(f"Cache exists check failed: {e}")
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self._enabled:
            return 0
        
        try:
            self._ensure_enabled()
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except CacheConfigurationError:
            return 0
        except redis.RedisError as e:
            logger.error(f"Redis CLEAR PATTERN error for '{pattern}': {e}")
            raise CacheOperationError(f"Cache clear pattern failed: {e}")
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values at once"""
        if not self._enabled or not keys:
            return {}
        
        try:
            self._ensure_enabled()
            values = self._client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    result[key] = self._deserialize(value)
            return result
        except CacheConfigurationError:
            return {}
        except redis.RedisError as e:
            logger.error(f"Redis MGET error: {e}")
            raise CacheOperationError(f"Cache get_many failed: {e}")
    
    def set_many(self, mapping: Dict[str, Any], ttl_seconds: Optional[int] = None) -> bool:
        """Set multiple key-value pairs at once"""
        if not self._enabled or not mapping:
            return False
        
        try:
            self._ensure_enabled()
            ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
            
            # Use pipeline for efficiency
            pipe = self._client.pipeline()
            for key, value in mapping.items():
                serialized = self._serialize(value)
                pipe.setex(key, ttl, serialized)
            pipe.execute()
            return True
        except CacheConfigurationError:
            return False
        except redis.RedisError as e:
            logger.error(f"Redis MSET error: {e}")
            raise CacheOperationError(f"Cache set_many failed: {e}")
    
    def increment(self, key: str, delta: int = 1) -> int:
        """Increment counter by delta"""
        if not self._enabled:
            return 0
        
        try:
            self._ensure_enabled()
            return self._client.incrby(key, delta)
        except CacheConfigurationError:
            return 0
        except redis.RedisError as e:
            logger.error(f"Redis INCR error for key '{key}': {e}")
            raise CacheOperationError(f"Cache increment failed: {e}")
    
    def ping(self) -> bool:
        """Test Redis connection"""
        if not self._enabled or not self._client:
            return False
        
        try:
            self._client.ping()
            return True
        except redis.RedisError:
            return False


# Singleton instance for easy import
_cache_service_instance = None


def get_cache_service() -> RedisAdapter:
    """
    Get singleton cache service instance.
    
    Lazy initialization - loads config from DB on first call.
    """
    global _cache_service_instance
    if _cache_service_instance is None:
        _cache_service_instance = RedisAdapter()
    return _cache_service_instance


def reset_cache_service():
    """
    Reset cache service singleton (useful after config changes).
    
    Call this from admin after updating CrawlCacheConfig.
    """
    global _cache_service_instance
    _cache_service_instance = None
    logger.info("Cache service singleton reset")
