"""Cache management for improved performance."""

from functools import lru_cache, wraps
from typing import Any, Callable, Dict, Optional, TypeVar, cast
import time
import logging
from datetime import datetime, timedelta
import redis
from redis.connection import ConnectionPool
import pickle
import hashlib
import json

logger = logging.getLogger('CacheManager')

T = TypeVar('T')

class CacheManager:
    """Manages caching for the application."""
    
    def __init__(self,
                 redis_url: Optional[str] = None,
                 default_ttl: int = 3600):
        """Initialize cache manager."""
        self.default_ttl = default_ttl
        self._redis_pool = None
        if redis_url:
            self._redis_pool = ConnectionPool.from_url(redis_url)
            
    @property
    def redis(self) -> Optional[redis.Redis]:
        """Get Redis connection from pool."""
        if self._redis_pool:
            return redis.Redis(connection_pool=self._redis_pool)
        return None
        
    def cache_key(self, prefix: str, *args: Any, **kwargs: Any) -> str:
        """Generate cache key from arguments."""
        key_dict = {
            'args': args,
            'kwargs': kwargs
        }
        key_str = json.dumps(key_dict, sort_keys=True)
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
        
    def cached(self,
              ttl: Optional[int] = None,
              prefix: Optional[str] = None,
              condition: Callable[..., bool] = lambda *args, **kwargs: True) -> Callable:
        """Decorator for caching function results."""
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            func_ttl = ttl or self.default_ttl
            func_prefix = prefix or func.__name__
            
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                if not condition(*args, **kwargs):
                    return func(*args, **kwargs)
                    
                cache_key = self.cache_key(func_prefix, *args, **kwargs)
                
                # Try Redis first
                if self.redis:
                    cached_value = self.redis.get(cache_key)
                    if cached_value:
                        return cast(T, pickle.loads(cached_value))
                        
                    result = func(*args, **kwargs)
                    self.redis.setex(
                        cache_key,
                        func_ttl,
                        pickle.dumps(result)
                    )
                    return result
                    
                # Fallback to in-memory cache
                return cast(
                    T,
                    lru_cache(maxsize=1000, ttl=func_ttl)(func)(*args, **kwargs)
                )
                
            return wrapper
        return decorator
        
    def invalidate(self, prefix: str, *args: Any, **kwargs: Any) -> None:
        """Invalidate cache for given prefix and arguments."""
        cache_key = self.cache_key(prefix, *args, **kwargs)
        if self.redis:
            self.redis.delete(cache_key)
            
    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate all keys matching pattern."""
        if self.redis:
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
                
class MarketDataCache:
    """Specialized cache for market data."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        
    @property
    def cached_price(self) -> Callable:
        """Cache decorator for price data."""
        return self.cache_manager.cached(
            ttl=60,  # 1 minute for price data
            prefix='price',
            condition=lambda symbol, *args, **kwargs:
                not kwargs.get('real_time', False)  # Don't cache real-time requests
        )
        
    @property
    def cached_ohlcv(self) -> Callable:
        """Cache decorator for OHLCV data."""
        return self.cache_manager.cached(
            ttl=300,  # 5 minutes for OHLCV
            prefix='ohlcv'
        )
        
    @property
    def cached_orderbook(self) -> Callable:
        """Cache decorator for orderbook data."""
        return self.cache_manager.cached(
            ttl=10,  # 10 seconds for orderbook
            prefix='orderbook'
        )
        
class AnalyticsCache:
    """Specialized cache for analytics data."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        
    @property
    def cached_metrics(self) -> Callable:
        """Cache decorator for performance metrics."""
        return self.cache_manager.cached(
            ttl=3600,  # 1 hour for metrics
            prefix='metrics'
        )
        
    @property
    def cached_risk_analysis(self) -> Callable:
        """Cache decorator for risk analysis."""
        return self.cache_manager.cached(
            ttl=1800,  # 30 minutes for risk analysis
            prefix='risk'
        )
        
# Global cache manager instance
cache_manager = CacheManager(
    redis_url='redis://localhost:6379/0'
    if 'REDIS_URL' not in globals()
    else REDIS_URL
)

# Specialized caches
market_cache = MarketDataCache(cache_manager)
analytics_cache = AnalyticsCache(cache_manager)
