"""Solscan API client implementation."""

import logging
from typing import Dict, Any, Optional
import aiohttp
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TokenMetadata:
    """Token metadata from Solscan."""
    address: str
    symbol: str
    name: str
    decimals: int
    holder_count: int
    market_cap: float
    price: float
    volume_24h: float
    supply: Dict[str, float]

class SolscanClient:
    """Client for interacting with Solscan API."""
    
    def __init__(self, api_key: str, base_url: str = "https://public-api.solscan.io"):
        """Initialize Solscan client.
        
        Args:
            api_key: Solscan API key
            base_url: Base URL for Solscan API
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = aiohttp.ClientSession()
        
        # Add required headers for Cloudflare and API authentication
        self.headers = {
            'Token': api_key,
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Origin': 'https://solscan.io',
            'Referer': 'https://solscan.io/',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make request to Solscan API with retry logic.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request arguments
            
        Returns:
            API response data
        """
        max_retries = 3
        retry_delay = 1  # Initial delay in seconds
        
        for attempt in range(max_retries):
            try:
                # Add random delay between requests to avoid rate limiting
                if attempt > 0:
                    time.sleep(retry_delay + (attempt * 0.5))
                    
                url = f"{self.base_url}/{endpoint.lstrip('/')}"
                async with self.session.request(method, url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=10), **kwargs) as response:
                    if response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"Rate limited by Solscan, waiting {retry_after}s")
                        time.sleep(retry_after)
                        continue
                        
                    if response.status == 403:  # Cloudflare block
                        logger.warning("Blocked by Cloudflare, adding delay before retry")
                        time.sleep(5)  # Add longer delay for Cloudflare blocks
                        continue
                        
                    if response.status == 404:
                        logger.warning(f"Resource not found: {url}")
                        return None
                        
                    if response.status != 200:
                        logger.warning(f"Request failed: {response.status} - {await response.text()}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                        return None
                        
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                if attempt == max_retries - 1:
                    logger.error(f"Request failed after {max_retries} attempts: {str(e)}")
                    return None
                logger.warning(f"Request error: {str(e)}, retrying in {retry_delay}s")
                time.sleep(retry_delay)
                retry_delay *= 2
                
        return None
        
    def _get_token_url(self, token_address: str) -> str:
        """Get token URL.
        
        Args:
            token_address: Token address
            
        Returns:
            Token URL
        """
        # Special case for native SOL
        if token_address == "So11111111111111111111111111111111111111112":
            return f"{self.base_url}/v2/token/SOL"
        return f"{self.base_url}/v2/token/{token_address}"
        
    async def get_token_metadata(self, token_address: str) -> Optional[TokenMetadata]:
        """Get token metadata.
        
        Args:
            token_address: Token mint address
            
        Returns:
            Token metadata if found
        """
        try:
            url = self._get_token_url(token_address)
            async with self.session.get(
                url,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Extract relevant fields from v2 API response
                    return TokenMetadata(
                        address=token_address,
                        symbol=data.get('symbol', ''),
                        name=data.get('name', ''),
                        decimals=data.get('decimals', 0),
                        holder_count=data.get('holderCount', 0),
                        market_cap=float(data.get('marketCap', 0)),
                        price=float(data.get('price', 0)),
                        volume_24h=float(data.get('volume24h', 0)),
                        supply={
                            'total': float(data.get('supply', {}).get('total', 0)),
                            'circulating': float(data.get('supply', {}).get('circulating', 0))
                        }
                    )
                elif response.status == 404:
                    if token_address == "So11111111111111111111111111111111111111112":
                        # Return hardcoded metadata for SOL
                        return TokenMetadata(
                            address="So11111111111111111111111111111111111111112",
                            symbol="SOL",
                            name="Solana",
                            decimals=9,
                            holder_count=0,
                            market_cap=0.0,
                            price=0.0,
                            volume_24h=0.0,
                            supply={
                                'total': 0.0,
                                'circulating': 0.0
                            }
                        )
                logger.warning(f"Resource not found: {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting token metadata: {str(e)}")
            return None
            
    async def get_token_holders(self, token_address: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get token holders.
        
        Args:
            token_address: Token mint address
            limit: Number of holders to return
            offset: Offset for pagination
            
        Returns:
            Token holders information
        """
        return await self._make_request(
            'GET',
            f'token/holders/{token_address}',
            params={'limit': limit, 'offset': offset}
        )
        
    async def get_token_market(self, token_address: str) -> Dict[str, Any]:
        """Get token market information.
        
        Args:
            token_address: Token mint address
            
        Returns:
            Token market information
        """
        return await self._make_request('GET', f'market/token/{token_address}')
        
    async def test_connection(self) -> bool:
        """Test connection to Solscan API.
        
        Returns:
            True if connection successful
        """
        try:
            # Test with SOL token metadata
            metadata = await self.get_token_metadata("So11111111111111111111111111111111111111112")
            if metadata:
                logger.info("Successfully connected to Solscan API")
                return True
                
            logger.warning("No data found for SOL token")
            return False
            
        except Exception as e:
            logger.error(f"Solscan connection test failed: {str(e)}")
            return False
