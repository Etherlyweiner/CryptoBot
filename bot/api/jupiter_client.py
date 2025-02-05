"""Jupiter DEX API client."""

import logging
import aiohttp
from typing import Dict, Any, List, Optional
from decimal import Decimal
import asyncio

logger = logging.getLogger(__name__)

class JupiterClient:
    """Jupiter DEX API client for token swaps."""
    
    def __init__(self, rpc_url: str):
        """Initialize Jupiter client.
        
        Args:
            rpc_url: Helius RPC URL for Solana network
        """
        self.rpc_url = rpc_url
        self.session = None
        self.base_url = "https://quote-api.jup.ag/v6"
        
    async def __aenter__(self):
        """Create aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close aiohttp session."""
        await self._close_session()
        
    async def _close_session(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def _ensure_session(self):
        """Ensure we have an active session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
    async def get_token_list(self) -> List[Dict[str, Any]]:
        """Get list of supported tokens.
        
        Returns:
            List of token information dictionaries
        """
        try:
            await self._ensure_session()
            
            # Add retry logic for token list
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with self.session.get(
                        f"{self.base_url}/tokens",
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Jupiter API v6 returns a list of token addresses
                            if isinstance(data, list):
                                logger.info(f"Successfully fetched {len(data)} token addresses from Jupiter")
                                # Convert addresses to token info format
                                tokens = [{"address": addr} for addr in data]
                                return tokens
                            # Handle old API format (unlikely)
                            elif isinstance(data, dict) and "tokens" in data:
                                logger.info(f"Successfully fetched {len(data['tokens'])} tokens from Jupiter (old format)")
                                return data["tokens"]
                            else:
                                logger.warning(f"Unexpected token list format from Jupiter API: {type(data)}")
                                if attempt < max_retries - 1:
                                    await asyncio.sleep(2 ** attempt)
                                    continue
                                return []
                        else:
                            logger.warning(f"Failed to fetch token list (attempt {attempt + 1}/{max_retries}): HTTP {response.status}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2 ** attempt)
                                continue
                            return []
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout while fetching token list (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return []
                    
                except Exception as e:
                    logger.error(f"Error fetching token list (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to get token list: {str(e)}")
            return []
            
    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 100,  # 1%
        only_direct_routes: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get quote for token swap.
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount of input tokens (in smallest units)
            slippage_bps: Slippage tolerance in basis points (1 bp = 0.01%)
            only_direct_routes: If True, only consider direct swap routes
            
        Returns:
            Quote information or None if failed
        """
        try:
            await self._ensure_session()
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),
                "slippageBps": slippage_bps,
                "onlyDirectRoutes": only_direct_routes,
                "asLegacyTransaction": True
            }
            
            async with self.session.get(
                f"{self.base_url}/quote",
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get quote: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting quote: {str(e)}")
            return None
            
    async def get_swap_transaction(
        self,
        quote: Dict[str, Any],
        user_public_key: str,
        priority_fee: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get swap transaction for a quote.
        
        Args:
            quote: Quote from get_quote()
            user_public_key: User's wallet public key
            priority_fee: Optional priority fee in lamports
            
        Returns:
            Transaction data or None if failed
        """
        try:
            await self._ensure_session()
            data = {
                "quoteResponse": quote,
                "userPublicKey": user_public_key,
                "asLegacyTransaction": True
            }
            
            if priority_fee is not None:
                data["priorityFee"] = priority_fee
                
            async with self.session.post(
                f"{self.base_url}/swap",
                json=data
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get swap transaction: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting swap transaction: {str(e)}")
            return None
