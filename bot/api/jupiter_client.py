"""Jupiter DEX API client."""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Union

import aiohttp
from aiohttp import ClientTimeout

logger = logging.getLogger(__name__)

class JupiterClient:
    """Client for interacting with Jupiter DEX API."""
    
    def __init__(self, rpc_url: str):
        """Initialize Jupiter client.
        
        Args:
            rpc_url: Solana RPC URL to use
        """
        self.rpc_url = rpc_url
        self.base_url = "https://quote-api.jup.ag/v6"
        self.session = None
        self.token_list = None
        self.wsol_address = "So11111111111111111111111111111111111111112"
        
    async def _ensure_session(self) -> None:
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            timeout = ClientTimeout(total=30)  # Increased timeout
            self.session = aiohttp.ClientSession(timeout=timeout)
            
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make HTTP request with retries.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional arguments for request
            
        Returns:
            Response data
            
        Raises:
            Exception if request fails after retries
        """
        await self._ensure_session()
        
        max_retries = 3
        base_delay = 1  # Start with 1 second delay
        
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/{endpoint}"
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 429:  # Rate limited
                        retry_after = int(response.headers.get('Retry-After', base_delay))
                        logger.warning(f"Rate limited, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue
                        
                    response.raise_for_status()
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                else:
                    raise
                    
    async def test_connection(self) -> bool:
        """Test connection to Jupiter API.
        
        Returns:
            True if connection successful
        """
        try:
            # Try to get token list as connection test
            await self.get_token_list(force_refresh=True)
            return True
        except Exception as e:
            logger.error(f"Jupiter API connection test failed: {str(e)}")
            return False
            
    async def get_token_list(self, force_refresh: bool = False) -> List[Dict]:
        """Get list of supported tokens.
        
        Args:
            force_refresh: Force refresh token list
            
        Returns:
            List of token info dictionaries
        """
        if self.token_list is None or force_refresh:
            try:
                response = await self._request('GET', 'tokens')
                if isinstance(response, str):
                    # Handle case where response is a string instead of JSON
                    logger.error(f"Unexpected string response from token list API: {response}")
                    return []
                    
                self.token_list = response.get('data', [])
                if not self.token_list:
                    logger.warning("Empty token list received")
                    
            except Exception as e:
                logger.error(f"Failed to get token list: {str(e)}")
                return []
                
        return self.token_list
        
    def find_token(self, symbol: str) -> Optional[Dict]:
        """Find token by symbol.
        
        Args:
            symbol: Token symbol
            
        Returns:
            Token info dictionary or None if not found
        """
        if not self.token_list:
            return None
            
        symbol = symbol.upper()
        for token in self.token_list:
            if token.get('symbol', '').upper() == symbol:
                return token
        return None
        
    async def get_quote(self, 
                       input_mint: str,
                       output_mint: str,
                       amount: Union[int, Decimal],
                       slippage: Decimal) -> Optional[Dict]:
        """Get quote for swap.
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount of input token (in lamports/smallest units)
            slippage: Maximum slippage percentage
            
        Returns:
            Quote data or None if quote fails
        """
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),
                "slippageBps": int(slippage * 100),  # Convert percentage to basis points
                "onlyDirectRoutes": "true",  # Prefer direct routes for better pricing
                "asLegacyTransaction": "true"  # Use legacy transactions for better compatibility
            }
            
            return await self._request('GET', 'quote', params=params)
            
        except Exception as e:
            logger.error(f"Failed to get quote: {str(e)}")
            return None
            
    async def close(self):
        """Close client session."""
        if self.session and not self.session.closed:
            await self.session.close()
