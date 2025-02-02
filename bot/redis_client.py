"""
Redis client for development and production.
"""
import asyncio
import json
import socket
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self, host='localhost', port=6380):
        self.host = host
        self.port = port
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
    
    async def connect(self):
        """Connect to Redis server."""
        try:
            self._reader, self._writer = await asyncio.open_connection(
                self.host, self.port
            )
            await self._send_command('ping')
            logger.info("Connected to Redis server")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {str(e)}")
            raise
    
    async def _send_command(self, command: str, *args) -> Any:
        """Send command to Redis server."""
        if not self._writer or not self._reader:
            await self.connect()
        
        try:
            request = {
                'command': command,
                'args': args
            }
            
            self._writer.write(json.dumps(request).encode())
            await self._writer.drain()
            
            data = await self._reader.read(1024)
            response = json.loads(data.decode())
            
            if response['status'] == 'error':
                raise Exception(response['message'])
            
            return response.get('data')
            
        except Exception as e:
            logger.error(f"Error sending command: {str(e)}")
            raise
    
    async def ping(self) -> bool:
        """Test connection to Redis server."""
        try:
            response = await self._send_command('ping')
            return response == 'PONG'
        except:
            return False
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set key-value pair."""
        await self._send_command('set', key, value, ttl)
    
    async def get(self, key: str) -> Any:
        """Get value for key."""
        return await self._send_command('get', key)
    
    async def delete(self, key: str):
        """Delete key."""
        await self._send_command('delete', key)
    
    async def hset(self, key: str, field: str, value: Any):
        """Set hash field."""
        await self._send_command('hset', key, field, value)
    
    async def hget(self, key: str, field: str) -> Any:
        """Get hash field."""
        return await self._send_command('hget', key, field)
    
    async def close(self):
        """Close connection."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
            self._reader = None
