import pickle
from typing import Any, Optional
from datetime import datetime, timedelta

class SimpleCache:
    _instance = None
    _cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SimpleCache, cls).__new__(cls)
        return cls._instance
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache with optional TTL in seconds"""
        expiry = None
        if ttl is not None:
            expiry = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = (value, expiry)
        
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache, returns None if expired or not found"""
        if key not in self._cache:
            return None
            
        value, expiry = self._cache[key]
        if expiry is not None and datetime.now() > expiry:
            del self._cache[key]
            return None
            
        return value
        
    def delete(self, key: str) -> None:
        """Delete a key from the cache"""
        if key in self._cache:
            del self._cache[key]
            
    def clear(self) -> None:
        """Clear all items from the cache"""
        self._cache.clear()
