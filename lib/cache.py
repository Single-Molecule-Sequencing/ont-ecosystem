"""
ONT Ecosystem Cache Utilities - Simple caching for expensive operations

Usage:
    from lib.cache import FileCache, memoize, timed_cache

    # File-based cache
    cache = FileCache("my_analysis")
    if cache.has("result"):
        data = cache.get("result")
    else:
        data = expensive_computation()
        cache.set("result", data, ttl=3600)  # Cache for 1 hour

    # Function memoization
    @memoize
    def expensive_function(x):
        return x ** 2

    # Timed cache decorator
    @timed_cache(ttl=300)  # 5 minutes
    def fetch_data():
        return api_call()
"""

import functools
import hashlib
import json
import os
import pickle
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, Union

# Type variable for generic functions
T = TypeVar('T')

# Default cache directory
DEFAULT_CACHE_DIR = Path(os.environ.get(
    "ONT_CACHE_DIR",
    Path.home() / ".ont-ecosystem" / "cache"
))


@dataclass
class CacheEntry:
    """A single cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    ttl: Optional[float] = None  # Time-to-live in seconds
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.ttl is None:
            return False
        return time.time() > (self.created_at + self.ttl)

    @property
    def age(self) -> float:
        """Get age of entry in seconds"""
        return time.time() - self.created_at


class MemoryCache:
    """
    Simple in-memory cache with TTL support.

    Thread-safe for basic operations.
    """

    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        self._cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def get(self, key: str, default: T = None) -> Union[Any, T]:
        """Get value from cache"""
        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return default
        if entry.is_expired:
            del self._cache[key]
            self._misses += 1
            return default
        entry.hits += 1
        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache"""
        # Evict if at capacity
        if len(self._cache) >= self.max_size:
            self._evict_oldest()

        self._cache[key] = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl=ttl if ttl is not None else self.default_ttl
        )

    def has(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        entry = self._cache.get(key)
        if entry is None:
            return False
        if entry.is_expired:
            del self._cache[key]
            return False
        return True

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> int:
        """Clear all entries, return count"""
        count = len(self._cache)
        self._cache.clear()
        return count

    def _evict_oldest(self) -> None:
        """Evict oldest entry"""
        if not self._cache:
            return
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]

    def cleanup(self) -> int:
        """Remove expired entries, return count"""
        expired = [k for k, v in self._cache.items() if v.is_expired]
        for key in expired:
            del self._cache[key]
        return len(expired)

    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }


class FileCache:
    """
    File-based cache for persistent caching.

    Stores cached data as JSON or pickle files.
    """

    def __init__(
        self,
        namespace: str,
        cache_dir: Optional[Path] = None,
        default_ttl: Optional[float] = None,
        use_pickle: bool = False
    ):
        self.namespace = namespace
        self.cache_dir = (cache_dir or DEFAULT_CACHE_DIR) / namespace
        self.default_ttl = default_ttl
        self.use_pickle = use_pickle
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        """Get file path for key"""
        # Hash key for safe filename
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        ext = ".pkl" if self.use_pickle else ".json"
        return self.cache_dir / f"{key_hash}{ext}"

    def _get_meta_path(self, key: str) -> Path:
        """Get metadata file path"""
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{key_hash}.meta"

    def get(self, key: str, default: T = None) -> Union[Any, T]:
        """Get value from cache"""
        path = self._get_path(key)
        meta_path = self._get_meta_path(key)

        if not path.exists():
            return default

        # Check metadata for expiration
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                if meta.get("ttl"):
                    expires_at = meta["created_at"] + meta["ttl"]
                    if time.time() > expires_at:
                        path.unlink()
                        meta_path.unlink()
                        return default
            except Exception:
                pass

        # Load value
        try:
            if self.use_pickle:
                with open(path, "rb") as f:
                    return pickle.load(f)
            else:
                return json.loads(path.read_text())
        except Exception:
            return default

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache"""
        path = self._get_path(key)
        meta_path = self._get_meta_path(key)

        # Write value
        try:
            if self.use_pickle:
                with open(path, "wb") as f:
                    pickle.dump(value, f)
            else:
                path.write_text(json.dumps(value, default=str))
        except Exception:
            return

        # Write metadata
        meta = {
            "key": key,
            "created_at": time.time(),
            "ttl": ttl if ttl is not None else self.default_ttl,
        }
        meta_path.write_text(json.dumps(meta))

    def has(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        return self.get(key, default=None) is not None

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        path = self._get_path(key)
        meta_path = self._get_meta_path(key)

        deleted = False
        if path.exists():
            path.unlink()
            deleted = True
        if meta_path.exists():
            meta_path.unlink()

        return deleted

    def clear(self) -> int:
        """Clear all entries"""
        count = 0
        for path in self.cache_dir.iterdir():
            try:
                path.unlink()
                count += 1
            except Exception:
                pass
        return count

    def cleanup(self) -> int:
        """Remove expired entries"""
        count = 0
        for meta_path in self.cache_dir.glob("*.meta"):
            try:
                meta = json.loads(meta_path.read_text())
                if meta.get("ttl"):
                    expires_at = meta["created_at"] + meta["ttl"]
                    if time.time() > expires_at:
                        # Find and remove data file
                        key_hash = meta_path.stem
                        for ext in [".json", ".pkl"]:
                            data_path = self.cache_dir / f"{key_hash}{ext}"
                            if data_path.exists():
                                data_path.unlink()
                                count += 1
                        meta_path.unlink()
            except Exception:
                pass
        return count

    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        files = list(self.cache_dir.glob("*"))
        data_files = [f for f in files if f.suffix in [".json", ".pkl"]]
        total_size = sum(f.stat().st_size for f in files)

        return {
            "namespace": self.namespace,
            "entries": len(data_files),
            "total_size_bytes": total_size,
            "cache_dir": str(self.cache_dir),
        }


# Decorators

def memoize(func: Callable[..., T]) -> Callable[..., T]:
    """
    Simple memoization decorator.

    Caches function results based on arguments.
    """
    cache: Dict[str, Any] = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Create cache key from arguments
        key = str((args, sorted(kwargs.items())))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    wrapper.cache = cache
    wrapper.cache_clear = lambda: cache.clear()
    return wrapper


def timed_cache(ttl: float = 300, max_size: int = 100):
    """
    Decorator for caching function results with TTL.

    Args:
        ttl: Time-to-live in seconds (default 5 minutes)
        max_size: Maximum cache size
    """
    cache = MemoryCache(max_size=max_size, default_ttl=ttl)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = str((args, sorted(kwargs.items())))
            if cache.has(key):
                return cache.get(key)
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result

        wrapper.cache = cache
        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_stats = lambda: cache.stats
        return wrapper

    return decorator


def disk_cache(namespace: str, ttl: Optional[float] = None):
    """
    Decorator for disk-based caching.

    Args:
        namespace: Cache namespace (creates subdirectory)
        ttl: Time-to-live in seconds
    """
    cache = FileCache(namespace, default_ttl=ttl)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = f"{func.__name__}:{str((args, sorted(kwargs.items())))}"
            if cache.has(key):
                return cache.get(key)
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result

        wrapper.cache = cache
        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_stats = lambda: cache.stats
        return wrapper

    return decorator


# Utility functions

def get_cache_dir() -> Path:
    """Get the cache directory path"""
    return DEFAULT_CACHE_DIR


def clear_all_caches() -> Dict[str, int]:
    """Clear all file caches"""
    results = {}
    if DEFAULT_CACHE_DIR.exists():
        for namespace_dir in DEFAULT_CACHE_DIR.iterdir():
            if namespace_dir.is_dir():
                cache = FileCache(namespace_dir.name)
                results[namespace_dir.name] = cache.clear()
    return results


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics for all caches"""
    stats = {
        "cache_dir": str(DEFAULT_CACHE_DIR),
        "namespaces": {},
    }

    if DEFAULT_CACHE_DIR.exists():
        for namespace_dir in DEFAULT_CACHE_DIR.iterdir():
            if namespace_dir.is_dir():
                cache = FileCache(namespace_dir.name)
                stats["namespaces"][namespace_dir.name] = cache.stats

    return stats
