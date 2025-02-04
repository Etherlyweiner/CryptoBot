"""Solscan API client implementation."""

import logging
from typing import Dict, Any, Optional
import requests
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
    
    def __init__(self, api_key: str, base_url: str = "https://public-api.solscan.io/v2"):
        """Initialize Solscan client.
        
        Args:
            api_key: Solscan API key
            base_url: Base URL for Solscan API
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Token': api_key,  # Changed back to Token header
            'Accept': 'application/json',
            'User-Agent': 'CryptoBot/1.0'
        })
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make request to Solscan API with retry logic.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request arguments
            
        Returns:
            API response data
            
        Raises:
            requests.exceptions.RequestException: If request fails after retries
        """
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}{endpoint}"
                response = self.session.request(method, url, **kwargs)
                
                if response.status_code == 429:  # Rate limit
                    retry_after = int(response.headers.get('Retry-After', retry_delay))
                    logger.warning(f"Rate limited by Solscan API, waiting {retry_after}s")
                    time.sleep(retry_after)
                    continue
                    
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Request failed: {str(e)}, retrying in {retry_delay}s")
                time.sleep(retry_delay)
                retry_delay *= 2
                
        raise requests.exceptions.RequestException("Max retries exceeded")
        
    def get_account_info(self, address: str) -> Dict[str, Any]:
        """Get account information.
        
        Args:
            address: Solana account address
            
        Returns:
            Account information
        """
        return self._make_request('GET', f'/account/{address}')
        
    def get_token_info(self, token_address: str) -> TokenMetadata:
        """Get token information.
        
        Args:
            token_address: Token mint address
            
        Returns:
            Token metadata
        """
        data = self._make_request('GET', f'/token/{token_address}')
        
        return TokenMetadata(
            address=data['address'],
            symbol=data.get('symbol', ''),
            name=data.get('name', ''),
            decimals=data.get('decimals', 0),
            holder_count=data.get('holderCount', 0),
            market_cap=data.get('marketCapFD', 0.0),
            price=data.get('priceUst', 0.0),
            volume_24h=data.get('volume24h', 0.0),
            supply={
                'total': data.get('supply', {}).get('total', 0.0),
                'circulating': data.get('supply', {}).get('circulating', 0.0),
            }
        )
        
    def get_token_holders(self, token_address: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get token holders.
        
        Args:
            token_address: Token mint address
            limit: Number of holders to return
            offset: Offset for pagination
            
        Returns:
            Token holders information
        """
        return self._make_request(
            'GET',
            f'/token/holders/{token_address}',
            params={'limit': limit, 'offset': offset}
        )
        
    def get_token_market(self, token_address: str) -> Dict[str, Any]:
        """Get token market information.
        
        Args:
            token_address: Token mint address
            
        Returns:
            Token market information
        """
        return self._make_request('GET', f'/token/market/{token_address}')
        
    def test_connection(self) -> bool:
        """Test connection to Solscan API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to get SOL token info as a test
            self.get_token_info("So11111111111111111111111111111111111111112")
            return True
        except Exception as e:
            logger.error(f"Solscan connection test failed: {str(e)}")
            return False
