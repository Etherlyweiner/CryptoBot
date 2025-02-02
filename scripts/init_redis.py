"""
Initialize Redis for caching.
"""
import asyncio
import redis.asyncio as aioredis
import json
from pathlib import Path

async def init_redis():
    """Initialize Redis with default configuration."""
    try:
        # Connect to Redis
        redis = await aioredis.from_url('redis://localhost')
        
        # Test connection
        await redis.ping()
        print("Successfully connected to Redis")
        
        # Set some default configuration
        default_config = {
            "cache_ttl": 3600,
            "max_memory": "100mb",
            "max_memory_policy": "allkeys-lru",
            "save_frequency": 900  # 15 minutes
        }
        
        # Store default configuration
        await redis.hset("cryptobot:config:cache", mapping=default_config)
        print("Initialized Redis with default configuration")
        
        # Close connection
        await redis.close()
        
    except Exception as e:
        print(f"Error initializing Redis: {str(e)}")
        print("Please ensure Redis is installed and running on localhost:6379")

if __name__ == "__main__":
    asyncio.run(init_redis())
