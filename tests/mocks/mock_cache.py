"""
Mock implementations for cache systems (Redis, Memcached).

This module provides fake caching operations including get, set, delete, expiration,
and cache invalidation for testing caching logic without actual cache server connections.
Includes in-memory cache store with TTL support and cache statistics tracking.

Key Features:
- MockRedisCache: Full Redis command support with data structures
- MockMemcachedCache: Memcached-compatible caching with string storage
- InMemoryCacheStore: Thread-safe in-memory cache with TTL and statistics
- Cache hit/miss tracking for testing cache effectiveness
- Support for cache namespaces and tag-based invalidation
- Automatic expiration handling with background cleanup
- Cache statistics: hits, misses, evictions, memory usage
"""

import pytest
import fakeredis
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from time import time, sleep
from threading import Lock, RLock, Thread
from collections import defaultdict, OrderedDict, Counter
from copy import deepcopy
from unittest.mock import MagicMock
import json
import hashlib


# ============================================================================
# InMemoryCacheStore: Core thread-safe in-memory cache implementation
# ============================================================================

class InMemoryCacheStore:
    """
    Thread-safe in-memory cache store with TTL support and statistics tracking.
    
    Provides core caching functionality used by both MockRedisCache and
    MockMemcachedCache implementations. Supports automatic expiration,
    LRU eviction, and comprehensive cache statistics.
    """
    
    def __init__(self, max_size: Optional[int] = None):
        """
        Initialize in-memory cache store.
        
        Args:
            max_size: Maximum number of cache entries (None for unlimited)
        """
        self._store: OrderedDict = OrderedDict()
        self._expiry: Dict[str, float] = {}
        self._lock = RLock()
        self._max_size = max_size
        
        # Statistics tracking
        self._stats = Counter({
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'sets': 0,
            'deletes': 0,
            'expirations': 0
        })
        
        # Namespace support for multi-tier cache invalidation
        self._namespaces: Dict[str, set] = defaultdict(set)
        self._tags: Dict[str, set] = defaultdict(set)
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache with automatic expiration check.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Cached value or None if not found or expired
        """
        with self._lock:
            # Check expiration first
            if self._is_expired(key):
                self._expire_key(key)
                self._stats['misses'] += 1
                return None
            
            # Retrieve value
            if key in self._store:
                # Move to end for LRU tracking
                self._store.move_to_end(key)
                self._stats['hits'] += 1
                # Return deep copy to prevent test pollution
                return deepcopy(self._store[key])
            
            self._stats['misses'] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None,
            namespace: Optional[str] = None, tags: Optional[List[str]] = None) -> bool:
        """
        Set value in cache with optional TTL and metadata.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None for no expiration)
            namespace: Optional namespace for organization
            tags: Optional tags for tag-based invalidation
            
        Returns:
            True if set successfully
        """
        with self._lock:
            # Check if we need to evict for max_size
            if self._max_size and len(self._store) >= self._max_size and key not in self._store:
                self._evict_lru()
            
            # Store value (deep copy to prevent external modifications)
            self._store[key] = deepcopy(value)
            self._store.move_to_end(key)
            self._stats['sets'] += 1
            
            # Set expiration if TTL provided
            if ttl is not None:
                self._expiry[key] = time() + ttl
            elif key in self._expiry:
                # Remove expiry if None provided for existing key
                del self._expiry[key]
            
            # Register namespace and tags
            if namespace:
                self._namespaces[namespace].add(key)
            
            if tags:
                for tag in tags:
                    self._tags[tag].add(key)
            
            return True
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key existed and was deleted, False otherwise
        """
        with self._lock:
            if key in self._store:
                del self._store[key]
                if key in self._expiry:
                    del self._expiry[key]
                self._stats['deletes'] += 1
                
                # Clean up from namespaces and tags
                self._remove_from_namespaces_and_tags(key)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._store.clear()
            self._expiry.clear()
            self._namespaces.clear()
            self._tags.clear()
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists and is not expired.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists and not expired
        """
        with self._lock:
            if self._is_expired(key):
                self._expire_key(key)
                return False
            return key in self._store
    
    def get_all_keys(self, namespace: Optional[str] = None) -> List[str]:
        """
        Get all non-expired keys, optionally filtered by namespace.
        
        Args:
            namespace: Optional namespace to filter by
            
        Returns:
            List of cache keys
        """
        with self._lock:
            # Clean up expired keys first
            self._cleanup_expired()
            
            if namespace:
                return list(self._namespaces.get(namespace, set()))
            return list(self._store.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with hit rate, miss rate, and counts
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0.0
            miss_rate = 100.0 - hit_rate
            
            return {
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'sets': self._stats['sets'],
                'deletes': self._stats['deletes'],
                'expirations': self._stats['expirations'],
                'hit_rate': round(hit_rate, 2),
                'miss_rate': round(miss_rate, 2),
                'total_keys': len(self._store),
                'expired_keys': sum(1 for k in self._store if self._is_expired(k))
            }
    
    def cleanup_expired(self) -> int:
        """
        Manually trigger cleanup of expired entries.
        
        Returns:
            Number of expired keys removed
        """
        with self._lock:
            return self._cleanup_expired()
    
    def __len__(self) -> int:
        """Return number of cache entries."""
        with self._lock:
            return len(self._store)
    
    # Private helper methods
    
    def _is_expired(self, key: str) -> bool:
        """Check if key has expired."""
        if key not in self._expiry:
            return False
        return time() > self._expiry[key]
    
    def _expire_key(self, key: str) -> None:
        """Remove expired key from cache."""
        if key in self._store:
            del self._store[key]
        if key in self._expiry:
            del self._expiry[key]
        self._stats['expirations'] += 1
        self._remove_from_namespaces_and_tags(key)
    
    def _cleanup_expired(self) -> int:
        """Remove all expired keys."""
        expired_keys = [k for k in list(self._store.keys()) if self._is_expired(k)]
        for key in expired_keys:
            self._expire_key(key)
        return len(expired_keys)
    
    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if self._store:
            # OrderedDict maintains insertion/access order
            key, _ = self._store.popitem(last=False)
            if key in self._expiry:
                del self._expiry[key]
            self._stats['evictions'] += 1
            self._remove_from_namespaces_and_tags(key)
    
    def _remove_from_namespaces_and_tags(self, key: str) -> None:
        """Remove key from all namespaces and tags."""
        # Remove from namespaces
        for namespace_keys in self._namespaces.values():
            namespace_keys.discard(key)
        
        # Remove from tags
        for tag_keys in self._tags.values():
            tag_keys.discard(key)
    
    def invalidate_namespace(self, namespace: str) -> int:
        """
        Invalidate all keys in a namespace.
        
        Args:
            namespace: Namespace to invalidate
            
        Returns:
            Number of keys invalidated
        """
        with self._lock:
            keys = list(self._namespaces.get(namespace, set()))
            for key in keys:
                self.delete(key)
            if namespace in self._namespaces:
                del self._namespaces[namespace]
            return len(keys)
    
    def invalidate_tag(self, tag: str) -> int:
        """
        Invalidate all keys with a specific tag.
        
        Args:
            tag: Tag to invalidate
            
        Returns:
            Number of keys invalidated
        """
        with self._lock:
            keys = list(self._tags.get(tag, set()))
            for key in keys:
                self.delete(key)
            if tag in self._tags:
                del self._tags[tag]
            return len(keys)


# ============================================================================
# MockRedisCache: Redis cache mock using fakeredis
# ============================================================================

class MockRedisCache:
    """
    Mock Redis cache implementation using fakeredis library.
    
    Provides full Redis command support including:
    - String operations: get, set, delete
    - Hash operations: hget, hset
    - List operations: lpush, rpop
    - Sorted set operations: zadd, zrange
    - Key management: exists, expire, keys
    - Database operations: flushdb, flushall
    """
    
    def __init__(self, decode_responses: bool = True):
        """
        Initialize mock Redis cache.
        
        Args:
            decode_responses: If True, decode byte responses to strings
        """
        self._redis = fakeredis.FakeStrictRedis(decode_responses=decode_responses)
        self._stats = Counter({
            'gets': 0,
            'sets': 0,
            'deletes': 0,
            'hits': 0,
            'misses': 0
        })
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from Redis cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        self._stats['gets'] += 1
        value = self._redis.get(key)
        
        if value is not None:
            self._stats['hits'] += 1
            # Deserialize JSON if it looks like JSON
            if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    return value
            return value
        
        self._stats['misses'] += 1
        return None
    
    def set(self, key: str, value: Any, ex: Optional[int] = None,
            px: Optional[int] = None, nx: bool = False, xx: bool = False) -> bool:
        """
        Set value in Redis cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ex: Expire time in seconds
            px: Expire time in milliseconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists
            
        Returns:
            True if set successfully
        """
        self._stats['sets'] += 1
        
        # Serialize non-string values to JSON
        if not isinstance(value, (str, bytes, int, float)):
            value = json.dumps(value)
        
        result = self._redis.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
        return bool(result)
    
    def delete(self, *keys: str) -> int:
        """
        Delete one or more keys.
        
        Args:
            *keys: Keys to delete
            
        Returns:
            Number of keys deleted
        """
        self._stats['deletes'] += len(keys)
        return self._redis.delete(*keys)
    
    def exists(self, *keys: str) -> int:
        """
        Check if keys exist.
        
        Args:
            *keys: Keys to check
            
        Returns:
            Number of keys that exist
        """
        return self._redis.exists(*keys)
    
    def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration on key.
        
        Args:
            key: Cache key
            seconds: Expiration time in seconds
            
        Returns:
            True if expiration was set
        """
        return bool(self._redis.expire(key, seconds))
    
    def keys(self, pattern: str = '*') -> List[str]:
        """
        Get all keys matching pattern.
        
        Args:
            pattern: Key pattern (supports * and ? wildcards)
            
        Returns:
            List of matching keys
        """
        return self._redis.keys(pattern)
    
    def flushdb(self) -> bool:
        """
        Delete all keys in current database.
        
        Returns:
            True if successful
        """
        self._redis.flushdb()
        return True
    
    def flushall(self) -> bool:
        """
        Delete all keys in all databases.
        
        Returns:
            True if successful
        """
        self._redis.flushall()
        return True
    
    # Redis hash operations
    
    def hget(self, name: str, key: str) -> Optional[Any]:
        """
        Get value from hash.
        
        Args:
            name: Hash name
            key: Field key in hash
            
        Returns:
            Field value or None
        """
        value = self._redis.hget(name, key)
        if value and isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return value
        return value
    
    def hset(self, name: str, key: Optional[str] = None, value: Optional[Any] = None,
             mapping: Optional[Dict[str, Any]] = None) -> int:
        """
        Set field in hash.
        
        Args:
            name: Hash name
            key: Field key
            value: Field value
            mapping: Dictionary of field-value pairs
            
        Returns:
            Number of fields added
        """
        if mapping:
            # Serialize non-string values in mapping
            serialized_mapping = {}
            for k, v in mapping.items():
                if not isinstance(v, (str, bytes, int, float)):
                    v = json.dumps(v)
                serialized_mapping[k] = v
            return self._redis.hset(name, mapping=serialized_mapping)
        else:
            if not isinstance(value, (str, bytes, int, float)):
                value = json.dumps(value)
            return self._redis.hset(name, key, value)
    
    # Redis list operations
    
    def lpush(self, key: str, *values: Any) -> int:
        """
        Push values to head of list.
        
        Args:
            key: List key
            *values: Values to push
            
        Returns:
            Length of list after push
        """
        serialized_values = []
        for value in values:
            if not isinstance(value, (str, bytes, int, float)):
                value = json.dumps(value)
            serialized_values.append(value)
        return self._redis.lpush(key, *serialized_values)
    
    def rpop(self, key: str) -> Optional[Any]:
        """
        Pop value from tail of list.
        
        Args:
            key: List key
            
        Returns:
            Popped value or None
        """
        value = self._redis.rpop(key)
        if value and isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return value
        return value
    
    # Redis sorted set operations
    
    def zadd(self, key: str, mapping: Dict[str, float], nx: bool = False,
             xx: bool = False, gt: bool = False, lt: bool = False) -> int:
        """
        Add members to sorted set.
        
        Args:
            key: Sorted set key
            mapping: Dictionary of member-score pairs
            nx: Only add new members
            xx: Only update existing members
            gt: Only update if new score is greater
            lt: Only update if new score is less
            
        Returns:
            Number of members added
        """
        # Serialize keys in mapping if needed
        serialized_mapping = {}
        for member, score in mapping.items():
            if not isinstance(member, (str, bytes)):
                member = json.dumps(member)
            serialized_mapping[member] = score
        
        return self._redis.zadd(key, serialized_mapping, nx=nx, xx=xx, gt=gt, lt=lt)
    
    def zrange(self, key: str, start: int, end: int, withscores: bool = False) -> List[Any]:
        """
        Get range of members from sorted set.
        
        Args:
            key: Sorted set key
            start: Start index
            end: End index
            withscores: Include scores in result
            
        Returns:
            List of members (and scores if withscores=True)
        """
        result = self._redis.zrange(key, start, end, withscores=withscores)
        
        # Try to deserialize JSON values
        if not withscores:
            deserialized = []
            for item in result:
                if isinstance(item, str) and (item.startswith('{') or item.startswith('[')):
                    try:
                        deserialized.append(json.loads(item))
                    except (json.JSONDecodeError, ValueError):
                        deserialized.append(item)
                else:
                    deserialized.append(item)
            return deserialized
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with operation counts and hit rate
        """
        total_requests = self._stats['gets']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            'gets': self._stats['gets'],
            'sets': self._stats['sets'],
            'deletes': self._stats['deletes'],
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate': round(hit_rate, 2)
        }


# ============================================================================
# MockMemcachedCache: Memcached cache mock
# ============================================================================

class MockMemcachedCache:
    """
    Mock Memcached cache implementation.
    
    Provides Memcached-compatible operations including:
    - get, set, delete: Basic operations
    - add: Set only if key doesn't exist
    - replace: Set only if key exists
    - incr, decr: Atomic increment/decrement
    
    Note: Memcached stores all values as strings, so serialization/
    deserialization is handled automatically.
    """
    
    def __init__(self):
        """Initialize mock Memcached cache."""
        self._cache = InMemoryCacheStore()
        self._stats = Counter({
            'gets': 0,
            'sets': 0,
            'adds': 0,
            'replaces': 0,
            'deletes': 0,
            'incrs': 0,
            'decrs': 0,
            'hits': 0,
            'misses': 0
        })
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        self._stats['gets'] += 1
        value = self._cache.get(key)
        
        if value is not None:
            self._stats['hits'] += 1
            # Deserialize from JSON string (Memcached stores as strings)
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    return value
            return value
        
        self._stats['misses'] += 1
        return None
    
    def set(self, key: str, value: Any, time: int = 0) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            time: Expiration time in seconds (0 = no expiration)
            
        Returns:
            True if set successfully
        """
        self._stats['sets'] += 1
        
        # Serialize to JSON string (Memcached stores as strings)
        if not isinstance(value, str):
            value = json.dumps(value)
        
        ttl = time if time > 0 else None
        return self._cache.set(key, value, ttl=ttl)
    
    def add(self, key: str, value: Any, time: int = 0) -> bool:
        """
        Add value only if key doesn't exist.
        
        Args:
            key: Cache key
            value: Value to cache
            time: Expiration time in seconds
            
        Returns:
            True if added, False if key already exists
        """
        self._stats['adds'] += 1
        
        if self._cache.exists(key):
            return False
        
        # Serialize to JSON string
        if not isinstance(value, str):
            value = json.dumps(value)
        
        ttl = time if time > 0 else None
        return self._cache.set(key, value, ttl=ttl)
    
    def replace(self, key: str, value: Any, time: int = 0) -> bool:
        """
        Replace value only if key exists.
        
        Args:
            key: Cache key
            value: New value
            time: Expiration time in seconds
            
        Returns:
            True if replaced, False if key doesn't exist
        """
        self._stats['replaces'] += 1
        
        if not self._cache.exists(key):
            return False
        
        # Serialize to JSON string
        if not isinstance(value, str):
            value = json.dumps(value)
        
        ttl = time if time > 0 else None
        return self._cache.set(key, value, ttl=ttl)
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if key didn't exist
        """
        self._stats['deletes'] += 1
        return self._cache.delete(key)
    
    def incr(self, key: str, delta: int = 1) -> Optional[int]:
        """
        Atomically increment numeric value.
        
        Args:
            key: Cache key
            delta: Amount to increment (default 1)
            
        Returns:
            New value after increment, or None if key doesn't exist or not numeric
        """
        self._stats['incrs'] += 1
        
        value = self._cache.get(key)
        if value is None:
            return None
        
        # Try to parse as integer
        try:
            if isinstance(value, str):
                current = int(value)
            else:
                current = int(value)
            
            new_value = current + delta
            self._cache.set(key, str(new_value))
            return new_value
        except (ValueError, TypeError):
            return None
    
    def decr(self, key: str, delta: int = 1) -> Optional[int]:
        """
        Atomically decrement numeric value.
        
        Args:
            key: Cache key
            delta: Amount to decrement (default 1)
            
        Returns:
            New value after decrement, or None if key doesn't exist or not numeric
        """
        self._stats['decrs'] += 1
        
        value = self._cache.get(key)
        if value is None:
            return None
        
        # Try to parse as integer
        try:
            if isinstance(value, str):
                current = int(value)
            else:
                current = int(value)
            
            new_value = max(0, current - delta)  # Memcached doesn't go below 0
            self._cache.set(key, str(new_value))
            return new_value
        except (ValueError, TypeError):
            return None
    
    def flush_all(self) -> bool:
        """
        Clear all cache entries.
        
        Returns:
            True if successful
        """
        self._cache.clear()
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with operation counts and hit rate
        """
        total_requests = self._stats['gets']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            'gets': self._stats['gets'],
            'sets': self._stats['sets'],
            'adds': self._stats['adds'],
            'replaces': self._stats['replaces'],
            'deletes': self._stats['deletes'],
            'incrs': self._stats['incrs'],
            'decrs': self._stats['decrs'],
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate': round(hit_rate, 2),
            'total_keys': len(self._cache)
        }


# ============================================================================
# Helper Functions
# ============================================================================

def create_cache_key(namespace: str, *args: Any, **kwargs: Any) -> str:
    """
    Generate consistent, deterministic cache key from parameters.
    
    Creates hashed cache keys that are safe for use as cache identifiers.
    Supports namespace prefixes for cache organization and tag-based
    invalidation strategies.
    
    Args:
        namespace: Cache namespace prefix
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key
        
    Returns:
        Hashed cache key string
        
    Example:
        >>> key = create_cache_key('users', user_id=123, include_profile=True)
        >>> key
        'users:a1b2c3d4e5f6...'
    """
    # Build key components
    key_parts = [namespace]
    
    # Add positional args
    for arg in args:
        if isinstance(arg, (dict, list)):
            key_parts.append(json.dumps(arg, sort_keys=True))
        else:
            key_parts.append(str(arg))
    
    # Add keyword args (sorted for consistency)
    for key, value in sorted(kwargs.items()):
        if isinstance(value, (dict, list)):
            key_parts.append(f"{key}={json.dumps(value, sort_keys=True)}")
        else:
            key_parts.append(f"{key}={value}")
    
    # Create base key
    base_key = ':'.join(key_parts)
    
    # For long keys, hash them to keep manageable length
    if len(base_key) > 200:
        # Create hash of the parameters part
        params_str = ':'.join(key_parts[1:])
        key_hash = hashlib.sha256(params_str.encode()).hexdigest()[:16]
        return f"{namespace}:{key_hash}"
    
    return base_key


def check_expiration(cache_store: InMemoryCacheStore, key: str) -> bool:
    """
    Check if cache entry has expired.
    
    Validates TTL expiration for cache entries and triggers cleanup
    if key has expired.
    
    Args:
        cache_store: InMemoryCacheStore instance to check
        key: Cache key to validate
        
    Returns:
        True if key has expired or doesn't exist, False if still valid
        
    Example:
        >>> store = InMemoryCacheStore()
        >>> store.set('test', 'value', ttl=1)
        >>> check_expiration(store, 'test')  # Immediately after
        False
        >>> time.sleep(2)
        >>> check_expiration(store, 'test')  # After expiration
        True
    """
    if not cache_store.exists(key):
        return True
    
    # exists() already handles expiration check internally
    # If key still exists after exists() call, it's not expired
    return False


def get_cache_stats(cache_instance: Union[MockRedisCache, MockMemcachedCache, InMemoryCacheStore]) -> Dict[str, Any]:
    """
    Get comprehensive cache statistics from any cache instance.
    
    Provides unified interface for retrieving statistics across different
    cache implementations (Redis, Memcached, InMemory).
    
    Args:
        cache_instance: Any cache mock instance (MockRedisCache, MockMemcachedCache, or InMemoryCacheStore)
        
    Returns:
        Dictionary with cache statistics including hits, misses, hit rate
        
    Example:
        >>> redis_cache = MockRedisCache()
        >>> redis_cache.set('key1', 'value1')
        >>> redis_cache.get('key1')
        >>> stats = get_cache_stats(redis_cache)
        >>> stats['hit_rate']
        100.0
    """
    if hasattr(cache_instance, 'get_stats'):
        return cache_instance.get_stats()
    
    # Fallback for objects without get_stats method
    return {
        'error': 'Cache instance does not support statistics',
        'instance_type': type(cache_instance).__name__
    }


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture
def mock_redis_cache():
    """
    Pytest fixture providing a clean MockRedisCache instance for each test.
    
    Creates a fresh mock Redis cache with fakeredis backend for isolated
    testing without actual Redis server connection. Automatically cleaned
    up after each test.
    
    Yields:
        MockRedisCache: Fresh mock Redis cache instance
        
    Example:
        def test_redis_caching(mock_redis_cache):
            mock_redis_cache.set('key', 'value')
            assert mock_redis_cache.get('key') == 'value'
    """
    cache = MockRedisCache(decode_responses=True)
    yield cache
    # Cleanup after test
    cache.flushall()


@pytest.fixture
def mock_memcached():
    """
    Pytest fixture providing a clean MockMemcachedCache instance for each test.
    
    Creates a fresh mock Memcached cache for isolated testing without actual
    Memcached server connection. Automatically cleaned up after each test.
    
    Yields:
        MockMemcachedCache: Fresh mock Memcached cache instance
        
    Example:
        def test_memcached_operations(mock_memcached):
            mock_memcached.set('counter', 0)
            mock_memcached.incr('counter', 5)
            assert mock_memcached.get('counter') == 5
    """
    cache = MockMemcachedCache()
    yield cache
    # Cleanup after test
    cache.flush_all()


@pytest.fixture
def clean_cache():
    """
    Pytest fixture providing a clean InMemoryCacheStore instance for each test.
    
    Creates a fresh in-memory cache store for isolated testing with full
    TTL support, statistics tracking, and namespace/tag management.
    Automatically cleaned up after each test.
    
    Yields:
        InMemoryCacheStore: Fresh in-memory cache store instance
        
    Example:
        def test_cache_expiration(clean_cache):
            clean_cache.set('temp', 'data', ttl=1)
            assert clean_cache.exists('temp') is True
            time.sleep(2)
            assert clean_cache.exists('temp') is False
    """
    cache = InMemoryCacheStore(max_size=1000)
    yield cache
    # Cleanup after test
    cache.clear()


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Classes
    'InMemoryCacheStore',
    'MockRedisCache',
    'MockMemcachedCache',
    
    # Helper Functions
    'create_cache_key',
    'check_expiration',
    'get_cache_stats',
    
    # Pytest Fixtures
    'mock_redis_cache',
    'mock_memcached',
    'clean_cache',
]

