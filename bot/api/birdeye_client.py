"""Birdeye API client for token price and market data."""

import logging
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class BirdeyeClient:
    """Client for interacting with the Birdeye API."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Birdeye client.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.base_url = config.get('apis', {}).get('birdeye', {}).get('base_url', 'https://public-api.birdeye.so')
        self.session: Optional[aiohttp.ClientSession] = None
        self.price_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_duration = 60  # Cache prices for 60 seconds
        
    async def initialize(self):
        """Initialize the client."""
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.info("Initialized Birdeye API client")
            
    async def close(self):
        """Close the client session."""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def get_token_price(self, token_address: str) -> Optional[float]:
        """Get current price of a token.
        
        Args:
            token_address: Token mint address
            
        Returns:
            float: Token price in USD or None if failed
        """
        try:
            # Check cache
            cache_entry = self.price_cache.get(token_address)
            if cache_entry:
                cache_time = cache_entry['timestamp']
                if (datetime.now() - cache_time).total_seconds() < self.cache_duration:
                    return cache_entry['price']
                    
            if not self.session:
                await self.initialize()
                
            url = f"{self.base_url}/public/price"
            params = {'address': token_address}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success'):
                        price = float(data['data']['value'])
                        self.price_cache[token_address] = {
                            'price': price,
                            'timestamp': datetime.now()
                        }
                        return price
                        
            logger.warning(f"Failed to get price for token {token_address}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting token price: {str(e)}")
            return None
            
    async def get_token_metadata(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Get token metadata.
        
        Args:
            token_address: Token mint address
            
        Returns:
            Dict: Token metadata or None if failed
        """
        try:
            if not self.session:
                await self.initialize()
                
            url = f"{self.base_url}/public/token"
            params = {'address': token_address}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success'):
                        return data['data']
                        
            logger.warning(f"Failed to get metadata for token {token_address}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting token metadata: {str(e)}")
            return None
            
    async def get_market_depth(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Get market depth for a token.
        
        Args:
            token_address: Token mint address
            
        Returns:
            Dict: Market depth data or None if failed
        """
        try:
            if not self.session:
                await self.initialize()
                
            url = f"{self.base_url}/public/market-depth"
            params = {'address': token_address}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success'):
                        return data['data']
                        
            logger.warning(f"Failed to get market depth for token {token_address}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting market depth: {str(e)}")
            return None
