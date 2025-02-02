import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
import aiohttp
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime
from wallet import PhantomWallet, WalletError, TransactionError

logger = logging.getLogger('CryptoBot.Trading')

@dataclass
class TradeConfig:
    slippage_bps: int = 50  # 0.5% slippage tolerance
    max_retries: int = 3
    retry_delay: int = 1
    min_sol_balance: float = 0.05  # Minimum SOL to keep for fees
    simulation_required: bool = True

@dataclass
class TradeResult:
    success: bool
    input_amount: float
    output_amount: Optional[float]
    price: Optional[float]
    timestamp: datetime
    error: Optional[str] = None
    transaction_id: Optional[str] = None

class TradingEngine:
    def __init__(self, wallet: PhantomWallet, config: Optional[TradeConfig] = None):
        self.wallet = wallet
        self.config = config or TradeConfig()
        self.jupiter_quote_api = os.getenv('JUPITER_QUOTE_API', 'https://quote-api.jup.ag/v4')
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
        
    async def get_quote(self, input_token: str, output_token: str, amount: float) -> Optional[Dict[str, Any]]:
        """Get swap quote from Jupiter"""
        try:
            session = await self._get_session()
            params = {
                'inputMint': input_token,
                'outputMint': output_token,
                'amount': str(int(amount * 1e9)),  # Convert to lamports
                'slippageBps': self.config.slippage_bps
            }
            
            async with session.get(f"{self.jupiter_quote_api}/quote", params=params) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Failed to get quote: {response.status}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting quote: {str(e)}")
            return None
            
    async def prepare_swap_transaction(self, quote: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Prepare swap transaction using Jupiter API"""
        try:
            session = await self._get_session()
            user_public_key = str(self.wallet.get_public_key())
            
            # Prepare the swap transaction
            async with session.post(
                f"{self.jupiter_quote_api}/swap",
                json={
                    "quoteResponse": quote,
                    "userPublicKey": user_public_key,
                    "wrapUnwrapSOL": True
                }
            ) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Failed to prepare swap: {response.status}")
                return None
                
        except Exception as e:
            logger.error(f"Error preparing swap transaction: {str(e)}")
            return None
            
    async def execute_trade(
        self,
        input_token: str,
        output_token: str,
        amount: float
    ) -> TradeResult:
        """Execute a trade with retry logic and proper error handling"""
        try:
            # Verify wallet connection
            if not self.wallet.is_connected:
                raise WalletError("Wallet not connected")
                
            # Check minimum SOL balance
            sol_balance = await self.wallet.get_balance()
            if sol_balance is None or sol_balance < self.config.min_sol_balance:
                raise TransactionError(f"Insufficient SOL balance for fees: {sol_balance}")
                
            # Get quote
            quote = await self.get_quote(input_token, output_token, amount)
            if not quote:
                raise TransactionError("Failed to get quote")
                
            # Calculate price
            price = float(quote['outAmount']) / float(quote['inAmount'])
            
            # Prepare transaction
            swap_transaction = await self.prepare_swap_transaction(quote)
            if not swap_transaction:
                raise TransactionError("Failed to prepare swap transaction")
                
            # Execute with retries
            for attempt in range(self.config.max_retries):
                try:
                    # Simulate first if required
                    if self.config.simulation_required:
                        simulation = await self.wallet.client.simulate_transaction(
                            swap_transaction['swapTransaction']
                        )
                        if simulation.value.err:
                            raise TransactionError(f"Simulation failed: {simulation.value.err}")
                    
                    # Sign and send transaction
                    signed_tx = await self.wallet.sign_transaction(swap_transaction['swapTransaction'])
                    if not signed_tx:
                        raise TransactionError("Failed to sign transaction")
                        
                    result = await self.wallet.client.send_transaction(signed_tx)
                    if result.value:
                        return TradeResult(
                            success=True,
                            input_amount=amount,
                            output_amount=float(quote['outAmount']) / 1e9,
                            price=price,
                            timestamp=datetime.utcnow(),
                            transaction_id=str(result.value)
                        )
                        
                except Exception as e:
                    if attempt == self.config.max_retries - 1:
                        raise
                    logger.warning(f"Retry {attempt + 1}/{self.config.max_retries}: {str(e)}")
                    await asyncio.sleep(self.config.retry_delay)
                    
            raise TransactionError("Max retries exceeded")
            
        except Exception as e:
            logger.error(f"Trade execution failed: {str(e)}")
            return TradeResult(
                success=False,
                input_amount=amount,
                output_amount=None,
                price=None,
                timestamp=datetime.utcnow(),
                error=str(e)
            )
            
    async def close(self):
        """Clean up resources"""
        if self._session and not self._session.closed:
            await self._session.close()
