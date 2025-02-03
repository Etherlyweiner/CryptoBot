import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
import aiohttp
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime
from wallet import PhantomWallet, WalletError, TransactionError
from .meme_strategy import MemeStrategy
from solana.rpc.async_api import AsyncClient

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
        self.meme_strategy_config = {
            # Add meme strategy config here
        }
        self.meme_strategy = MemeStrategy(self.meme_strategy_config)
        self.client = AsyncClient(self.meme_strategy_config['rpc_url'])
        self.active_trades = {}
        self.trade_history = []
        
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
            
    async def scan_for_opportunities(self):
        """Scan for trading opportunities"""
        try:
            # Get trending tokens from DEXScreener
            trending = await self._get_trending_tokens()
            
            for token in trending:
                # Analyze each token
                analysis = await self.meme_strategy.analyze_token(token['address'])
                
                if analysis['tradeable']:
                    # Calculate position size
                    size = self._calculate_position_size(token)
                    
                    # Execute trade if conditions met
                    if size > 0:
                        await self.execute_trade(token['address'], size)
                        
        except Exception as e:
            logger.error(f"Error scanning opportunities: {str(e)}")
            
    async def execute_trade(self, token_address: str, size: float):
        """Execute trade with safety checks"""
        try:
            # Validate one more time before trading
            validation = await self.meme_strategy.validator.validate_token(token_address)
            if not validation['valid']:
                logger.warning(f"Final validation failed: {validation['reason']}")
                return
                
            # Check if we have enough balance
            balance = await self._check_balance()
            if balance < size:
                logger.warning(f"Insufficient balance: {balance} < {size}")
                return
                
            # Execute buy order
            tx = await self._place_order(token_address, size, "buy")
            if not tx:
                logger.error("Failed to place buy order")
                return
                
            # Record trade
            trade_id = f"{token_address}-{datetime.now().timestamp()}"
            self.active_trades[trade_id] = {
                "token": token_address,
                "size": size,
                "entry_time": datetime.now(),
                "entry_price": await self._get_token_price(token_address)
            }
            
            logger.info(f"Successfully entered trade {trade_id}")
            
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            
    async def monitor_positions(self):
        """Monitor and manage open positions"""
        try:
            for trade_id, trade in self.active_trades.items():
                # Get exit strategy
                exit_strategy = await self.meme_strategy.get_exit_strategy(
                    trade['token'],
                    trade['entry_price']
                )
                
                if exit_strategy['action'] == 'sell':
                    # Execute sell
                    await self._close_position(trade_id, exit_strategy['reason'])
                    
        except Exception as e:
            logger.error(f"Error monitoring positions: {str(e)}")
            
    async def _close_position(self, trade_id: str, reason: str):
        """Close a trading position"""
        try:
            trade = self.active_trades[trade_id]
            
            # Execute sell order
            tx = await self._place_order(trade['token'], trade['size'], "sell")
            if not tx:
                logger.error(f"Failed to close position {trade_id}")
                return
                
            # Calculate profit/loss
            exit_price = await self._get_token_price(trade['token'])
            profit = (exit_price - trade['entry_price']) * trade['size']
            
            # Record trade result
            self.trade_history.append({
                **trade,
                "exit_time": datetime.now(),
                "exit_price": exit_price,
                "profit": profit,
                "reason": reason
            })
            
            # Remove from active trades
            del self.active_trades[trade_id]
            
            logger.info(f"Closed position {trade_id} with profit {profit} SOL")
            
        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
            
    async def _get_trending_tokens(self) -> list:
        """Get trending tokens from DEXScreener"""
        # Implement trending token fetching
        return []
        
    def _calculate_position_size(self, token: Dict) -> float:
        """Calculate appropriate position size"""
        try:
            # Implement position sizing logic
            return 0.1  # Default to 0.1 SOL
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return 0
            
    async def _check_balance(self) -> float:
        """Check wallet balance"""
        try:
            # Implement balance check
            return 0.0
        except Exception as e:
            logger.error(f"Error checking balance: {str(e)}")
            return 0
            
    async def _place_order(self, token_address: str, size: float, side: str) -> Optional[str]:
        """Place order on DEX"""
        try:
            # Implement order placement
            return None
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            return None
            
    async def _get_token_price(self, token_address: str) -> float:
        """Get current token price"""
        try:
            # Implement price fetching
            return 0.0
        except Exception as e:
            logger.error(f"Error getting token price: {str(e)}")
            return 0
            
    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
