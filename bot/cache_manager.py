"""
Cache manager for API responses and frequently accessed data.
"""

import time
from typing import Dict, Any, Optional, List, Tuple
from functools import lru_cache
import logging
from dataclasses import dataclass
import aiohttp
import asyncio
from datetime import datetime, timedelta
import json
import os
import shutil
from pathlib import Path
from prometheus_client import Counter, Gauge
import aiofiles
import pickle
import zlib
from concurrent.futures import ThreadPoolExecutor
from .redis_client import RedisClient

logger = logging.getLogger(__name__)

# Prometheus metrics
CACHE_HITS = Counter('cache_hits_total', 'Total number of cache hits')
CACHE_MISSES = Counter('cache_misses_total', 'Total number of cache misses')
CACHE_SIZE = Gauge('cache_size_bytes', 'Total size of cache in bytes')
BACKUP_COUNT = Counter('cache_backups_total', 'Total number of cache backups created')

@dataclass
class CacheEntry:
    """Cache entry with data and expiration."""
    data: Any
    expires_at: float
    last_accessed: float
    access_count: int
    size_bytes: int

class CacheManager:
    """Enhanced cache manager with advanced features."""
    
    def __init__(self, 
                 max_size_bytes: int = 1024 * 1024 * 100,  # 100MB
                 cleanup_interval: int = 3600,  # 1 hour
                 backup_interval: int = 86400,  # 24 hours
                 cache_dir: str = "cache"):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size_bytes = max_size_bytes
        self.current_size_bytes = 0
        self.cleanup_interval = cleanup_interval
        self.backup_interval = backup_interval
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.backup_dir = self.cache_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Initialize Redis client
        self.redis = RedisClient()
        
        # Initialize locks
        self.cache_lock = asyncio.Lock()
        self.size_lock = asyncio.Lock()
        self.backup_lock = asyncio.Lock()
        
        # Thread pool for compression operations
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # Start background tasks
        asyncio.create_task(self._periodic_cleanup())
        asyncio.create_task(self._periodic_backup())
        asyncio.create_task(self._init_redis())
        
        # Load existing cache if available
        self._load_cache()

    async def _init_redis(self):
        """Initialize Redis connection."""
        try:
            await self.redis.connect()
            logger.info("Connected to Redis server")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {str(e)}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get item from cache with automatic expiration."""
        try:
            # Try Redis first
            value = await self.redis.get(key)
            if value is not None:
                return value
            
            # Fall back to local cache
            async with self.cache_lock:
                if key in self.cache:
                    entry = self.cache[key]
                    if entry.expires_at > time.time():
                        entry.last_accessed = time.time()
                        entry.access_count += 1
                        return entry.data
                    else:
                        await self._remove_entry(key)
            return None
            
        except Exception as e:
            logger.error(f"Error getting cache entry: {str(e)}")
            return None
    
    async def set(self, 
                  key: str, 
                  value: Any, 
                  ttl: int = 3600,
                  compress: bool = False) -> bool:
        """Set item in cache with optional compression."""
        try:
            # Try Redis first
            await self.redis.set(key, value, ttl)
            
            # Also store in local cache
            data = value
            if compress:
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(
                    self.thread_pool,
                    lambda: zlib.compress(pickle.dumps(value))
                )
            
            size = await self._calculate_size(data)
            
            async with self.cache_lock:
                # Check if we need to evict entries
                while (self.current_size_bytes + size) > self.max_size_bytes:
                    if not await self._evict_entry():
                        return False
                
                # Add new entry
                self.cache[key] = CacheEntry(
                    data=data,
                    expires_at=time.time() + ttl,
                    last_accessed=time.time(),
                    access_count=0,
                    size_bytes=size
                )
                
                async with self.size_lock:
                    self.current_size_bytes += size
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache entry: {str(e)}")
            return False

    async def _remove_entry(self, key: str):
        """Remove an entry from the cache."""
        if key in self.cache:
            entry = self.cache.pop(key)
            async with self.size_lock:
                self.current_size_bytes -= entry.size_bytes
                CACHE_SIZE.set(self.current_size_bytes)

    async def _evict_entry(self) -> bool:
        """Evict least valuable entry from cache."""
        if not self.cache:
            return False
            
        # Score entries based on frequency and recency
        current_time = time.time()
        scores = {
            key: (entry.access_count / (current_time - entry.last_accessed + 1))
            for key, entry in self.cache.items()
        }
        
        if scores:
            # Remove entry with lowest score
            key_to_remove = min(scores.items(), key=lambda x: x[1])[0]
            await self._remove_entry(key_to_remove)
            return True
            
        return False

    async def _calculate_size(self, data: Any) -> int:
        """Calculate size of data in bytes."""
        if isinstance(data, (bytes, bytearray)):
            return len(data)
        return len(pickle.dumps(data))

    async def _periodic_cleanup(self):
        """Periodically clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                async with self.cache_lock:
                    current_time = time.time()
                    keys_to_remove = [
                        key for key, entry in self.cache.items()
                        if current_time > entry.expires_at
                    ]
                    
                    for key in keys_to_remove:
                        await self._remove_entry(key)
                        
                logger.info(f"Cleaned up {len(keys_to_remove)} expired cache entries")
                
            except Exception as e:
                logger.error(f"Error in cache cleanup: {str(e)}")

    async def _periodic_backup(self):
        """Periodically backup cache to disk."""
        while True:
            try:
                await asyncio.sleep(self.backup_interval)
                await self.backup_cache()
            except Exception as e:
                logger.error(f"Error in cache backup: {str(e)}")

    async def backup_cache(self):
        """Backup cache to disk."""
        try:
            async with self.backup_lock:
                # Create backup filename with timestamp
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                backup_path = self.backup_dir / f"cache_backup_{timestamp}.pkl"
                
                # Serialize cache data
                cache_data = {
                    'entries': self.cache,
                    'metadata': {
                        'timestamp': timestamp,
                        'size_bytes': self.current_size_bytes,
                        'num_entries': len(self.cache)
                    }
                }
                
                # Save to disk
                async with aiofiles.open(backup_path, 'wb') as f:
                    await f.write(pickle.dumps(cache_data))
                
                # Cleanup old backups (keep last 5)
                backup_files = sorted(self.backup_dir.glob('cache_backup_*.pkl'))
                for backup_file in backup_files[:-5]:
                    backup_file.unlink()
                
                BACKUP_COUNT.inc()
                logger.info(f"Cache backed up to {backup_path}")
                
        except Exception as e:
            logger.error(f"Error backing up cache: {str(e)}")

    def _load_cache(self):
        """Load cache from most recent backup."""
        try:
            backup_files = sorted(self.backup_dir.glob('cache_backup_*.pkl'))
            if not backup_files:
                return
                
            latest_backup = backup_files[-1]
            with open(latest_backup, 'rb') as f:
                cache_data = pickle.load(f)
                
            self.cache = cache_data['entries']
            self.current_size_bytes = cache_data['metadata']['size_bytes']
            CACHE_SIZE.set(self.current_size_bytes)
            
            logger.info(f"Loaded cache from backup: {latest_backup}")
            
        except Exception as e:
            logger.error(f"Error loading cache from backup: {str(e)}")

    async def clear(self):
        """Clear all cache entries."""
        async with self.cache_lock:
            self.cache.clear()
            self.current_size_bytes = 0
            CACHE_SIZE.set(0)

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'size_bytes': self.current_size_bytes,
            'max_size_bytes': self.max_size_bytes,
            'num_entries': len(self.cache),
            'utilization': self.current_size_bytes / self.max_size_bytes,
            'hit_rate': CACHE_HITS._value.get() / (CACHE_HITS._value.get() + CACHE_MISSES._value.get())
            if CACHE_HITS._value.get() + CACHE_MISSES._value.get() > 0 else 0
        }

    async def close(self):
        """Clean up resources."""
        try:
            self.thread_pool.shutdown()
            await self.redis.close()
        except Exception as e:
            logger.error(f"Error closing cache manager: {str(e)}")
