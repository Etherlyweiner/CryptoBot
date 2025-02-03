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
                'slippageBps': self.config.slippage_bps,
                'onlyDirectRoutes': False,
                'asLegacyTransaction': True
            }
            
            async with session.get(f"{self.jupiter_quote_api}/quote", params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to get quote: {error_text}")
                    return None
                    
                quote_data = await response.json()
                logger.info(f"Received quote for {amount} {input_token} -> {output_token}")
                return quote_data
                
        except Exception as e:
            logger.error(f"Error getting quote: {str(e)}")
            return None
            
    async def execute_swap(self, quote: Dict[str, Any]) -> TradeResult:
        """Execute a swap transaction using Jupiter"""
        start_time = datetime.now()
        input_amount = float(quote['inputAmount']) / 1e9
        
        try:
            # Verify wallet has enough balance
            balance = await self.wallet.get_balance()
            if balance < input_amount + self.config.min_sol_balance:
                raise TransactionError(f"Insufficient balance: {balance} SOL")
            
            # Get transaction data from Jupiter
            session = await self._get_session()
            swap_data = {
                'quoteResponse': quote,
                'userPublicKey': str(self.wallet._public_key),
                'wrapUnwrapSOL': True
            }
            
            async with session.post(f"{self.jupiter_quote_api}/swap", json=swap_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to prepare swap: {error_text}")
                    return TradeResult(
                        success=False,
                        input_amount=input_amount,
                        output_amount=None,
                        price=None,
                        timestamp=start_time,
                        error=f"Swap preparation failed: {error_text}"
                    )
                
                swap_response = await response.json()
                
                # Execute the transaction
                for attempt in range(self.config.max_retries):
                    try:
                        tx_signature = await self.wallet.sign_and_send_transaction(
                            swap_response['swapTransaction']
                        )
                        
                        # Wait for confirmation
                        status = await self.wallet.client.confirm_transaction(tx_signature)
                        if status.value.err:
                            raise TransactionError(f"Transaction failed: {status.value.err}")
                        
                        output_amount = float(quote['outputAmount']) / 1e9
                        price = output_amount / input_amount if input_amount > 0 else 0
                        
                        logger.info(f"Swap successful: {input_amount} -> {output_amount} ({price:.4f})")
                        return TradeResult(
                            success=True,
                            input_amount=input_amount,
                            output_amount=output_amount,
                            price=price,
                            timestamp=start_time,
                            transaction_id=str(tx_signature)
                        )
                        
                    except Exception as e:
                        if attempt < self.config.max_retries - 1:
                            logger.warning(f"Swap attempt {attempt + 1} failed, retrying: {str(e)}")
                            await asyncio.sleep(self.config.retry_delay)
                        else:
                            raise
                            
        except Exception as e:
            error_msg = f"Swap execution failed: {str(e)}"
            logger.error(error_msg)
            return TradeResult(
                success=False,
                input_amount=input_amount,
                output_amount=None,
                price=None,
                timestamp=start_time,
                error=error_msg
            )
            
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
                
            # Execute swap
            return await self.execute_swap(quote)
            
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
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
