"""Jupiter DEX API client for token swaps."""

import logging
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class JupiterClient:
    """Client for interacting with the Jupiter DEX API."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Jupiter client.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.base_url = config.get('apis', {}).get('jupiter', {}).get('base_url', 'https://quote-api.jup.ag/v6')
        self.session: Optional[aiohttp.ClientSession] = None
        self.token_list: Optional[List[Dict[str, Any]]] = None
        self.last_token_refresh = datetime.min
        self.token_refresh_interval = 3600  # Refresh token list every hour
        
    async def initialize(self):
        """Initialize the client."""
        if not self.session:
            self.session = aiohttp.ClientSession()
            await self.refresh_token_list()
            logger.info("Initialized Jupiter API client")
            
    async def close(self):
        """Close the client session."""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def refresh_token_list(self) -> bool:
        """Refresh the token list.
        
        Returns:
            bool: True if successful
        """
        try:
            if not self.session:
                await self.initialize()
                
            url = f"{self.base_url}/tokens"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self.token_list = data
                    self.last_token_refresh = datetime.now()
                    logger.info(f"Refreshed token list with {len(self.token_list)} tokens")
                    return True
                    
            logger.warning("Failed to refresh token list")
            return False
            
        except Exception as e:
            logger.error(f"Error refreshing token list: {str(e)}")
            return False
            
    def find_token(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Find token by symbol.
        
        Args:
            symbol: Token symbol (e.g., 'SOL')
            
        Returns:
            Dict: Token data or None if not found
        """
        if not self.token_list:
            return None
            
        symbol = symbol.upper()
        for token in self.token_list:
            if token.get('symbol', '').upper() == symbol:
                return token
                
        return None
        
    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 100
    ) -> Optional[Dict[str, Any]]:
        """Get swap quote.
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount in input token's smallest unit
            slippage_bps: Slippage tolerance in basis points (1 bp = 0.01%)
            
        Returns:
            Dict: Quote data or None if failed
        """
        try:
            if not self.session:
                await self.initialize()
                
            url = f"{self.base_url}/quote"
            params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': str(amount),
                'slippageBps': slippage_bps
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                    
            logger.warning("Failed to get swap quote")
            return None
            
        except Exception as e:
            logger.error(f"Error getting swap quote: {str(e)}")
            return None
            
    async def get_swap_transaction(
        self,
        quote: Dict[str, Any],
        user_public_key: str
    ) -> Optional[Dict[str, Any]]:
        """Get swap transaction.
        
        Args:
            quote: Quote data from get_quote()
            user_public_key: User's wallet public key
            
        Returns:
            Dict: Transaction data or None if failed
        """
        try:
            if not self.session:
                await self.initialize()
                
            url = f"{self.base_url}/swap"
            payload = {
                'quoteResponse': quote,
                'userPublicKey': user_public_key,
                'wrapUnwrapSOL': True
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                    
            logger.warning("Failed to get swap transaction")
            return None
            
        except Exception as e:
            logger.error(f"Error getting swap transaction: {str(e)}")
            return None
