"""Helius API client implementation."""

import logging
import json
import aiohttp
from typing import Dict, Any, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

class HeliusClient:
    """Client for interacting with Helius API."""
    
    def __init__(self, api_key: str, rpc_url: str):
        """Initialize Helius client.
        
        Args:
            api_key: Helius API key
            rpc_url: RPC URL for Helius API
        """
        self.api_key = api_key
        self.rpc_url = rpc_url.rstrip('/')  # Remove trailing slash if present
        self.session = None
        self.websocket = None
        
    async def test_connection(self) -> bool:
        """Test connection to Helius API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to get SOL balance as a test
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            # Use RPC method to get balance
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": ["So11111111111111111111111111111111111111112"]
            }
            
            async with self.session.post(
                f"{self.rpc_url}",
                headers={"Content-Type": "application/json"},
                params={"api-key": self.api_key},
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"{response.status}, message={error_text}, url={response.url}")
                    
                data = await response.json()
                if "result" not in data:
                    raise Exception(f"Invalid response: {data}")
                    
                return True
                
        except Exception as e:
            logger.error(f"Failed to test connection: {str(e)}")
            return False
            
    async def get_token_metadata(self, token_address: str) -> Dict[str, Any]:
        """Get token metadata from Helius API.
        
        Args:
            token_address: Token mint address
            
        Returns:
            Token metadata
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        # Use RPC method to get token metadata
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenMetadata",
            "params": [token_address]
        }
        
        async with self.session.post(
            f"{self.rpc_url}",
            headers={"Content-Type": "application/json"},
            params={"api-key": self.api_key},
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"{response.status}, message={error_text}, url={response.url}")
                
            data = await response.json()
            if "result" not in data:
                raise Exception(f"Invalid response: {data}")
                
            return data["result"]
            
    async def subscribe_mempool(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Subscribe to mempool updates.
        
        Args:
            callback: Async callback function to handle mempool updates
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        # Get base URL without path and convert to ws:// or wss://
        ws_url = self.rpc_url.replace('http://', 'ws://').replace('https://', 'wss://')
        ws_url = f"{ws_url}?api-key={self.api_key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url) as websocket:
                    self.websocket = websocket
                    
                    # Subscribe to mempool
                    await websocket.send_str(json.dumps({
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "mempoolSubscribe",
                        "params": {}
                    }))
                    
                    logger.info("Successfully subscribed to mempool updates")
                    
                    # Handle incoming messages
                    async for msg in websocket:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                                if "params" in data:
                                    await callback(data["params"])
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to decode message: {str(e)}")
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"WebSocket error: {websocket.exception()}")
                            break
                            
        except Exception as e:
            logger.error(f"Error in mempool subscription: {str(e)}")
            raise
            
        finally:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
