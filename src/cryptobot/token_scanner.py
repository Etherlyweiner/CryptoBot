"""Token scanner for monitoring new tokens"""
import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TokenScanner:
    """Scanner for monitoring new tokens"""
    
    def __init__(self, config: Dict):
        """Initialize token scanner"""
        self.config = config
        self.session = None
        self.cache = {}
        self.last_scan = None
        
        # Configure API endpoints
        self.birdeye_api_key = config.get('birdeye', {}).get('api_key')
        self.birdeye_url = config.get('birdeye', {}).get('base_url', 'https://public-api.birdeye.so')
        
        self.helius_api_key = config.get('helius', {}).get('api_key')
        self.helius_url = config.get('helius', {}).get('rpc_url')
        
        # Configure headers
        self.headers = {
            'Content-Type': 'application/json'
        }
        if self.birdeye_api_key:
            self.headers['X-API-KEY'] = self.birdeye_api_key
    
    async def __aenter__(self):
        """Async context manager enter"""
        await self._get_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def get_token_info(self, token_address: str) -> Optional[Dict]:
        """Get token information with caching"""
        try:
            # Check cache first
            if token_address in self.cache:
                cache_time, token_info = self.cache[token_address]
                if datetime.now() - cache_time < timedelta(seconds=self.config.get('cache_duration', 300)):
                    return token_info
            
            # Get token info from Birdeye
            birdeye_info = await self._get_birdeye_info(token_address)
            if not birdeye_info:
                return None
            
            # Get additional info from Helius if available
            helius_info = await self._get_helius_info(token_address) if self.helius_api_key else {}
            
            # Combine info
            token_info = {**birdeye_info, **helius_info}
            
            # Cache result
            self.cache[token_address] = (datetime.now(), token_info)
            
            return token_info
            
        except Exception as e:
            logger.error(f"Error getting token info: {str(e)}")
            return None
    
    async def _get_birdeye_info(self, token_address: str) -> Optional[Dict]:
        """Get token information from Birdeye"""
        try:
            if not self.session:
                await self._get_session()
            
            url = f"{self.birdeye_url}/public/token_data?address={token_address}"
            async with self.session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    logger.error(f"Request failed with status {response.status}")
                    return None
                    
                data = await response.json()
                if not data or 'data' not in data:
                    return None
                    
                return {
                    'price': data['data'].get('price', 0),
                    'liquidity_usd': data['data'].get('liquidity', 0),
                    'volume_24h': data['data'].get('volume24h', 0),
                    'market_cap': data['data'].get('marketCap', 0),
                    'price_change_24h': data['data'].get('priceChange24h', 0)
                }
                
        except Exception as e:
            logger.error(f"Error getting Birdeye info: {str(e)}")
            return None
    
    async def _get_helius_info(self, token_address: str) -> Optional[Dict]:
        """Get token information from Helius"""
        try:
            if not self.session:
                await self._get_session()
            
            payload = {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "getTokenSupply",
                "params": [token_address]
            }
            
            async with self.session.post(self.helius_url, json=payload, headers=self.headers) as response:
                if response.status != 200:
                    logger.error(f"Helius request failed with status {response.status}")
                    return None
                    
                data = await response.json()
                if not data or 'result' not in data:
                    return None
                    
                return {
                    'total_supply': data['result'].get('value', 0),
                    'decimals': data['result'].get('decimals', 0)
                }
                
        except Exception as e:
            logger.error(f"Error getting Helius info: {str(e)}")
            return None
    
    async def scan_new_tokens(self) -> List[Dict]:
        """Scan for new tokens"""
        try:
            if not self.session:
                await self._get_session()
            
            # Get current time
            now = datetime.now()
            
            # If last scan was less than 1 minute ago, skip
            if self.last_scan and (now - self.last_scan) < timedelta(minutes=1):
                return []
                
            self.last_scan = now
            
            # Get new tokens from Birdeye
            url = f"{self.birdeye_url}/public/new_tokens"
            async with self.session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    logger.error(f"Request failed with status {response.status}")
                    return []
                    
                data = await response.json()
                if not data or 'data' not in data:
                    return []
                    
                tokens = []
                for token in data['data']:
                    token_info = await self.get_token_info(token['address'])
                    if token_info:
                        tokens.append(token_info)
                        
                return tokens
                
        except Exception as e:
            logger.error(f"Error scanning new tokens: {str(e)}")
            return []
    
    async def _get_session(self):
        """Get aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close resources"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
