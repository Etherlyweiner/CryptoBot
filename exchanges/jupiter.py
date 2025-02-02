"""Jupiter DEX integration for Solana trading."""

import asyncio
import logging
from typing import Dict, List, Optional
from decimal import Decimal
import aiohttp
from dataclasses import dataclass
import base58
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solders.pubkey import Pubkey

logger = logging.getLogger('JupiterDEX')

@dataclass
class Route:
    """Trading route information."""
    in_amount: int
    out_amount: int
    price_impact_pct: float
    market_infos: List[Dict]
    slippage_bps: int
    
class JupiterDEX:
    """Jupiter DEX integration."""
    
    def __init__(self, config: Dict):
        """Initialize Jupiter DEX."""
        self.config = config
        self.api_url = 'https://quote-api.jup.ag/v4'
        self.client = AsyncClient(config.get('rpc_url', 'https://api.mainnet-beta.solana.com'))
        
    async def get_token_list(self) -> List[Dict]:
        """Get list of supported tokens."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/tokens") as response:
                return await response.json()
                
    async def get_price(self,
                       input_mint: str,
                       output_mint: str,
                       amount: int,
                       slippage_bps: int = 50) -> Optional[Route]:
        """Get price quote for a swap."""
        try:
            params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': str(amount),
                'slippageBps': slippage_bps
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/quote",
                    params=params
                ) as response:
                    data = await response.json()
                    
                    if 'data' not in data:
                        return None
                        
                    return Route(
                        in_amount=int(data['data']['inAmount']),
                        out_amount=int(data['data']['outAmount']),
                        price_impact_pct=float(data['data']['priceImpactPct']),
                        market_infos=data['data']['marketInfos'],
                        slippage_bps=slippage_bps
                    )
                    
        except Exception as e:
            logger.error(f"Failed to get price: {e}")
            return None
            
    async def get_swap_transaction(self,
                                 route: Route,
                                 user_public_key: Pubkey) -> Optional[Transaction]:
        """Get swap transaction for a route."""
        try:
            transaction_data = {
                'route': route,
                'userPublicKey': str(user_public_key),
                'wrapUnwrapSOL': True
            }
            
            async with aiohttp.ClientSession() as session:
                # Get serialized transaction
                async with session.post(
                    f"{self.api_url}/swap",
                    json=transaction_data
                ) as response:
                    data = await response.json()
                    
                    if 'swapTransaction' not in data:
                        return None
                        
                    # Deserialize transaction
                    serialized_tx = base58.b58decode(data['swapTransaction'])
                    return Transaction.deserialize(serialized_tx)
                    
        except Exception as e:
            logger.error(f"Failed to get swap transaction: {e}")
            return None
            
    async def execute_swap(self,
                          wallet,
                          input_mint: str,
                          output_mint: str,
                          amount: int,
                          slippage_bps: int = 50) -> Optional[str]:
        """Execute a token swap."""
        try:
            # Get price quote
            route = await self.get_price(
                input_mint,
                output_mint,
                amount,
                slippage_bps
            )
            
            if not route:
                raise Exception("Failed to get price quote")
                
            # Get swap transaction
            transaction = await self.get_swap_transaction(
                route,
                wallet.public_key
            )
            
            if not transaction:
                raise Exception("Failed to get swap transaction")
                
            # Sign transaction
            signed_tx = await wallet.sign_transaction(transaction)
            
            # Send transaction
            result = await self.client.send_transaction(
                signed_tx,
                commitment='confirmed'
            )
            
            return result.value
            
        except Exception as e:
            logger.error(f"Failed to execute swap: {e}")
            return None
            
    def calculate_price_impact(self, route: Route) -> float:
        """Calculate price impact percentage."""
        return route.price_impact_pct
        
    def validate_slippage(self,
                         route: Route,
                         max_slippage_bps: int = 100) -> bool:
        """Validate if slippage is within acceptable range."""
        return route.slippage_bps <= max_slippage_bps
        
    async def close(self):
        """Close DEX connection."""
        await self.client.close()
