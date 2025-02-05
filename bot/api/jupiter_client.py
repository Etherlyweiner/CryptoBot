"""Jupiter DEX API client."""

import logging
import aiohttp
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
import asyncio
import json

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
        self.base_url = "https://api.jup.ag"
        
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
            
            # First get tradable tokens
            try:
                async with self.session.get(
                    f"{self.base_url}/tokens/v1/mints/tradable",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        tradable_tokens = await response.json()
                        if isinstance(tradable_tokens, list):
                            logger.info(f"Successfully fetched {len(tradable_tokens)} tradable tokens")
                            
                            # Now get token metadata for each token in batches
                            tokens = []
                            batch_size = 50  # Process 50 tokens at a time
                            
                            for i in range(0, len(tradable_tokens), batch_size):
                                batch = tradable_tokens[i:i + batch_size]
                                batch_tasks = []
                                
                                for token_addr in batch:
                                    task = asyncio.create_task(self._get_token_metadata(token_addr))
                                    batch_tasks.append(task)
                                    
                                # Wait for all tasks in batch with timeout
                                try:
                                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                                    for result in batch_results:
                                        if isinstance(result, dict) and result:
                                            tokens.append(result)
                                except Exception as e:
                                    logger.warning(f"Error processing token metadata batch: {str(e)}")
                                    
                            if tokens:
                                logger.info(f"Successfully fetched metadata for {len(tokens)} tokens")
                                return tokens
                            else:
                                logger.warning("No token metadata found")
                                return [{"address": addr} for addr in tradable_tokens]
                                
                    elif response.status == 429:
                        logger.error("Rate limited by Jupiter API")
                        return []
                    else:
                        logger.error(f"Failed to fetch tradable tokens: HTTP {response.status}")
                        return []
                        
            except asyncio.TimeoutError:
                logger.error("Timeout while fetching tradable tokens")
                return []
                
            except Exception as e:
                logger.error(f"Error fetching tradable tokens: {str(e)}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get token list: {str(e)}")
            return []
            
    async def _get_token_metadata(self, token_addr: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific token.
        
        Args:
            token_addr: Token mint address
            
        Returns:
            Token metadata dictionary or None if not found
        """
        try:
            async with self.session.get(
                f"{self.base_url}/tokens/v1/token/{token_addr}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, dict):
                        return {
                            "address": token_addr,
                            "symbol": data.get("symbol", ""),
                            "decimals": data.get("decimals", 0),
                            "name": data.get("name", ""),
                            "coingeckoId": data.get("coingeckoId"),
                            "tags": data.get("tags", [])
                        }
                elif response.status != 404:  # Ignore 404s, just return None
                    logger.warning(f"Failed to fetch token metadata for {token_addr}: HTTP {response.status}")
                return None
                
        except Exception as e:
            logger.warning(f"Error fetching token metadata for {token_addr}: {str(e)}")
            return None
            
    async def get_price(self, token_addr: str, vs_token: str = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v") -> Optional[Decimal]:
        """Get token price in terms of another token (default USDC).
        
        Args:
            token_addr: Token mint address to get price for
            vs_token: Token mint address to price against (default USDC)
            
        Returns:
            Price as Decimal or None if not found
        """
        try:
            await self._ensure_session()
            
            async with self.session.get(
                f"{self.base_url}/price/v2",
                params={
                    "ids": token_addr,
                    "vsToken": vs_token
                },
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, dict) and "data" in data:
                        token_data = data["data"].get(token_addr)
                        if token_data and "price" in token_data:
                            return Decimal(str(token_data["price"]))
                elif response.status == 429:
                    logger.error("Rate limited by Jupiter price API")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get price for {token_addr}: {str(e)}")
            return None

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
