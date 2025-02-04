"""Helius API client."""

import logging
import asyncio
import aiohttp
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class HeliusClient:
    """Client for interacting with Helius API."""
    
    def __init__(self, api_key: str, rpc_url: Optional[str] = None):
        """Initialize Helius client.
        
        Args:
            api_key: Helius API key
            rpc_url: Optional custom RPC URL. If not provided, will use standard Helius RPC
        """
        self.api_key = api_key
        self.rpc_url = rpc_url or f"https://rpc.helius.xyz/?api-key={api_key}"
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.last_request_time = datetime.min
        self.request_count = 0
        self.rate_limit = 50  # Requests per second
        self.rate_window = timedelta(seconds=1)
        
    async def __aenter__(self):
        """Enter async context."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        await self._close_session()
        
    async def _close_session(self):
        """Close the aiohttp session."""
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.error(f"Error closing websocket: {str(e)}")
            self.ws = None
            
        if self.session:
            try:
                await self.session.close()
            except Exception as e:
                logger.error(f"Error closing session: {str(e)}")
            self.session = None
            
    async def _rate_limit_wait(self):
        """Wait if necessary to respect rate limits."""
        now = datetime.now()
        time_diff = now - self.last_request_time
        
        if time_diff < self.rate_window:
            if self.request_count >= self.rate_limit:
                wait_time = (self.rate_window - time_diff).total_seconds()
                if wait_time > 0:
                    logger.debug(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
                    self.request_count = 0
        else:
            self.request_count = 0
            
        self.last_request_time = now
        self.request_count += 1
        
    async def _make_request(self, method: str, params: list, retries: int = 3) -> Optional[Dict[str, Any]]:
        """Make a JSON-RPC request to Helius.
        
        Args:
            method: RPC method name
            params: List of parameters for the method
            retries: Number of retries for failed requests
            
        Returns:
            Response data if successful, None otherwise
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        await self._rate_limit_wait()
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        for attempt in range(retries):
            try:
                async with self.session.post(
                    self.rpc_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get('Retry-After', 5))
                        logger.warning(f"Rate limited, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue
                        
                    if response.status == 522:  # Cloudflare timeout
                        logger.warning("Cloudflare timeout, retrying...")
                        await asyncio.sleep(2 ** attempt)
                        continue
                        
                    response.raise_for_status()
                    data = await response.json()
                    
                    if "error" in data:
                        error = data["error"]
                        logger.error(f"RPC error: {error}")
                        return None
                        
                    return data.get("result")
                    
            except asyncio.TimeoutError:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{retries})")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    
            except Exception as e:
                logger.error(f"Request error (attempt {attempt + 1}/{retries}): {str(e)}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    
        return None
        
    async def test_connection(self) -> bool:
        """Test connection to Helius API.
        
        Returns:
            True if connection is successful
        """
        try:
            result = await self._make_request("getHealth", [])
            return result == "ok"
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
            
    async def subscribe_mempool(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Subscribe to mempool updates.
        
        Args:
            callback: Async callback function to handle updates
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        ws_url = f"wss://rpc.helius.xyz/?api-key={self.api_key}"
        
        try:
            self.ws = await self.session.ws_connect(
                ws_url,
                timeout=30,
                heartbeat=15
            )
            
            # Subscribe to mempool
            await self.ws.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "mempoolSubscribe",
                "params": []
            })
            
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = msg.json()
                        if "method" in data and data["method"] == "mempoolNotify":
                            await callback(data["params"][0])
                    except Exception as e:
                        logger.error(f"Error processing mempool message: {str(e)}")
                        
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning("WebSocket connection closed")
                    break
                    
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self.ws.exception()}")
                    break
                    
        except Exception as e:
            logger.error(f"WebSocket connection error: {str(e)}")
            raise
            
        finally:
            if self.ws:
                await self.ws.close()
                self.ws = None
