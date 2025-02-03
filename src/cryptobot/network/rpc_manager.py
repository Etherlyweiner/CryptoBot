"""
RPC Connection Manager for CryptoBot
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
from solana.rpc.async_api import AsyncClient
from solana.rpc.websocket_api import connect

logger = logging.getLogger(__name__)

class RPCManager:
    """Manages RPC connections with fallback support."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize RPC manager."""
        self.config_path = Path(config_path) if config_path else Path("config/rpc.json")
        self.current_endpoint = None
        self.clients: Dict[str, AsyncClient] = {}
        self.ws_clients = {}
        self.load_config()
        
    def load_config(self):
        """Load RPC configuration."""
        with open(self.config_path) as f:
            self.config = json.load(f)
        self.primary = self.config["primary"]
        self.fallbacks = self.config["fallback"]
        self.settings = self.config["settings"]
        
    async def get_client(self) -> AsyncClient:
        """Get the current RPC client."""
        if not self.current_endpoint:
            await self.initialize()
        return self.clients[self.current_endpoint]
    
    async def initialize(self):
        """Initialize RPC connections."""
        # Initialize primary
        success = await self._init_endpoint(self.primary)
        if success:
            self.current_endpoint = self.primary["name"]
            return
            
        # Try fallbacks
        for fallback in self.fallbacks:
            success = await self._init_endpoint(fallback)
            if success:
                self.current_endpoint = fallback["name"]
                return
                
        raise ConnectionError("Failed to connect to any RPC endpoint")
    
    async def _init_endpoint(self, endpoint_config: Dict) -> bool:
        """Initialize a single RPC endpoint."""
        try:
            name = endpoint_config["name"]
            client = AsyncClient(endpoint_config["url"])
            # Test connection
            await client.get_health()
            self.clients[name] = client
            
            # Initialize WebSocket if available
            if "ws_url" in endpoint_config:
                ws = await connect(endpoint_config["ws_url"])
                self.ws_clients[name] = ws
                
            logger.info(f"Successfully connected to {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {endpoint_config['name']}: {str(e)}")
            return False
    
    async def switch_endpoint(self):
        """Switch to a fallback endpoint."""
        current_name = self.current_endpoint
        
        # Try all other endpoints
        endpoints = [self.primary] + self.fallbacks
        for endpoint in endpoints:
            if endpoint["name"] != current_name:
                success = await self._init_endpoint(endpoint)
                if success:
                    self.current_endpoint = endpoint["name"]
                    logger.info(f"Switched to {endpoint['name']}")
                    return True
                    
        return False
    
    async def execute_with_retry(self, operation, *args, **kwargs):
        """Execute an RPC operation with retry logic."""
        retries = 0
        while retries < self.settings["max_retries"]:
            try:
                client = await self.get_client()
                return await operation(client, *args, **kwargs)
            except Exception as e:
                retries += 1
                logger.warning(f"RPC operation failed: {str(e)}")
                
                if retries < self.settings["max_retries"]:
                    await asyncio.sleep(self.settings["retry_delay"] / 1000)
                    if self.settings["switch_on_error"]:
                        await self.switch_endpoint()
                else:
                    raise
    
    async def close(self):
        """Close all connections."""
        for client in self.clients.values():
            await client.close()
        for ws in self.ws_clients.values():
            await ws.close()
