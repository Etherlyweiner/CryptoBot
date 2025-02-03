"""Main trading bot implementation."""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import json
from datetime import datetime
from dataclasses import dataclass, field
import aiohttp
import traceback
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
import base58

from bot.wallet.phantom_integration import PhantomWalletManager
from cache_manager import cache_manager, market_cache
from metrics_collector import metrics
from system_health import health_checker
from security_manager import security_manager

logger = logging.getLogger('TradingBot')

JUPITER_API_BASE = "https://price.jup.ag/v4"
SOLSCAN_API_BASE = "https://public-api.solscan.io/market"

@dataclass
class Trade:
    """Represents an active trade."""
    token_address: str  # Solana token mint address
    entry_price_sol: float
    quantity_tokens: float
    side: str  # 'buy' or 'sell'
    timestamp: datetime = field(default_factory=datetime.now)
    stop_loss_sol: Optional[float] = None
    take_profit_sol: Optional[float] = None
    status: str = 'open'  # 'open', 'closed', 'cancelled'
    transaction_signature: Optional[str] = None

@dataclass
class TradingConfig:
    """Trading configuration."""
    position_size_sol: float
    stop_loss_percent: float
    take_profit_percent: float
    max_slippage_percent: float
    network: str = 'mainnet-beta'
    max_positions: int = 5
    max_trades_per_day: int = 10
    order_timeout: int = 30

class TradingBot:
    """Solana memecoin trading bot implementation."""
    
    def __init__(self,
                 wallet: PhantomWalletManager,
                 config: TradingConfig):
        """Initialize trading bot."""
        self.wallet = wallet
        self.config = config
        self.is_running = False
        self.positions = {}
        self.active_trades: List[Trade] = []
        self.trades_today = 0
        self.last_trade_reset = datetime.now().date()
        self._trading_task = None
        self.MAX_RETRIES = 5
        self.RETRY_DELAY = 5
        
        # Initialize Solana client
        self.solana = AsyncClient(f"https://api.{self.config.network}.solana.com")
        
        # Initialize metrics
        self.trade_count = metrics.trade_count
        self.position_value = metrics.position_value
        self.pnl = metrics.pnl
        
        # Connect wallet if not already connected
        if not self.wallet.is_connected():
            success, message = self.wallet.connect()
            if not success:
                logger.error(f"Failed to connect wallet: {message}")
                raise RuntimeError(f"Failed to connect wallet: {message}")
        
        logger.debug("TradingBot initialized with config: %s", config)
    
    def get_sol_balance(self) -> float:
        """Get SOL balance in wallet."""
        try:
            return self.wallet.get_sol_balance()
        except Exception as e:
            logger.error(f"Failed to get SOL balance: {str(e)}")
            return 0.0
    
    def get_token_balance(self, token_address: str) -> float:
        """Get token balance for a specific SPL token."""
        try:
            return self.wallet.get_token_balance(token_address)
        except Exception as e:
            logger.error(f"Failed to get token balance: {str(e)}")
            return 0.0
    
    async def _get_token_price(self, token_address: str) -> Optional[float]:
        """Get current price of token in SOL."""
        try:
            # Get price from Jupiter API
            url = f"{JUPITER_API_BASE}/price?ids={token_address}&vsToken=SOL"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("data") and token_address in data["data"]:
                            return float(data["data"][token_address]["price"])
            return None
        except Exception as e:
            logger.error(f"Error getting token price: {str(e)}")
            return None
    
    async def _get_trending_tokens(self) -> List[str]:
        """Get list of trending token addresses."""
        try:
            # Get trending tokens from Solscan
            url = f"{SOLSCAN_API_BASE}/token/list?sortBy=volume&direction=desc&limit=20"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [token["address"] for token in data["data"] 
                               if self._is_valid_token(token)]
            return []
        except Exception as e:
            logger.error(f"Error getting trending tokens: {str(e)}")
            return []
    
    def _is_valid_token(self, token_data: Dict) -> bool:
        """Check if token meets our criteria."""
        try:
            # Basic validation criteria
            min_volume = 1000  # Minimum 1000 SOL daily volume
            min_holders = 100  # Minimum 100 holders
            
            return (
                float(token_data.get("volume24h", 0)) >= min_volume and
                int(token_data.get("holder", 0)) >= min_holders and
                token_data.get("verified", False)  # Only verified tokens
            )
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            return False
    
    async def _analyze_token(self, token_address: str) -> bool:
        """Analyze token for potential trade."""
        try:
            # Get token data from Solscan
            url = f"{SOLSCAN_API_BASE}/token/{token_address}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return False
                    
                    data = await response.json()
                    
                    # Analysis criteria
                    price_change_24h = float(data.get("priceChange24h", 0))
                    volume_24h = float(data.get("volume24h", 0))
                    market_cap = float(data.get("marketCap", 0))
                    
                    # Trading signals
                    signals = {
                        "price_dip": price_change_24h < -10,  # Price dropped more than 10%
                        "high_volume": volume_24h > 5000,     # Volume > 5000 SOL
                        "reasonable_mcap": 1000 <= market_cap <= 100000,  # Market cap between 1K-100K SOL
                        "sufficient_liquidity": await self._check_liquidity(token_address)
                    }
                    
                    # Log analysis
                    logger.info(f"Token analysis for {token_address}:")
                    logger.info(f"Price change 24h: {price_change_24h}%")
                    logger.info(f"Volume 24h: {volume_24h} SOL")
                    logger.info(f"Market cap: {market_cap} SOL")
                    logger.info(f"Signals: {signals}")
                    
                    return all(signals.values())
                    
        except Exception as e:
            logger.error(f"Error analyzing token: {str(e)}")
            return False
    
    async def _check_liquidity(self, token_address: str) -> bool:
        """Check if token has sufficient liquidity."""
        try:
            # Get liquidity info from Jupiter
            url = f"{JUPITER_API_BASE}/liquidity?tokens={token_address}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        liquidity = float(data.get("data", {}).get(token_address, {}).get("liquidityInSol", 0))
                        return liquidity >= 100  # Minimum 100 SOL liquidity
            return False
        except Exception as e:
            logger.error(f"Error checking liquidity: {str(e)}")
            return False
    
    async def _execute_trade(self, token_address: str):
        """Execute a trade using Jupiter."""
        try:
            # Get quote from Jupiter
            amount_in = self.config.position_size_sol * 10**9  # Convert to lamports
            
            # Get quote
            quote_url = f"{JUPITER_API_BASE}/quote"
            params = {
                "inputMint": "So11111111111111111111111111111111111111112",  # SOL mint
                "outputMint": token_address,
                "amount": str(int(amount_in)),
                "slippageBps": int(self.config.max_slippage_percent * 100)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(quote_url, params=params) as response:
                    if response.status != 200:
                        logger.error("Failed to get quote")
                        return
                    
                    quote_data = await response.json()
                    
                    # Get transaction data
                    swap_url = f"{JUPITER_API_BASE}/swap"
                    swap_data = {
                        "quoteResponse": quote_data,
                        "userPublicKey": self.wallet.public_key,
                        "wrapUnwrapSOL": True
                    }
                    
                    async with session.post(swap_url, json=swap_data) as swap_response:
                        if swap_response.status != 200:
                            logger.error("Failed to prepare swap transaction")
                            return
                        
                        swap_result = await swap_response.json()
                        
                        # Sign and send transaction
                        tx = Transaction.deserialize(base58.b58decode(swap_result["swapTransaction"]))
                        signed_tx = await self.wallet.sign_transaction(tx)
                        
                        # Send transaction
                        result = await self.solana.send_transaction(signed_tx)
                        signature = result.value
                        
                        # Create trade record
                        price = float(quote_data["outAmount"]) / float(quote_data["inAmount"])
                        quantity = float(quote_data["outAmount"]) / 10**9  # Convert from smallest unit
                        
                        trade = Trade(
                            token_address=token_address,
                            entry_price_sol=price,
                            quantity_tokens=quantity,
                            side="buy",
                            stop_loss_sol=price * (1 - self.config.stop_loss_percent),
                            take_profit_sol=price * (1 + self.config.take_profit_percent),
                            transaction_signature=signature
                        )
                        
                        self.active_trades.append(trade)
                        self.trades_today += 1
                        
                        logger.info(f"Trade executed: {trade}")
                        
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
    
    async def _close_position(self, trade: Trade, reason: str):
        """Close a position using Jupiter."""
        try:
            # Get quote for selling
            amount_in = int(trade.quantity_tokens * 10**9)  # Convert to smallest unit
            
            # Get quote
            quote_url = f"{JUPITER_API_BASE}/quote"
            params = {
                "inputMint": trade.token_address,
                "outputMint": "So11111111111111111111111111111111111111112",  # SOL mint
                "amount": str(amount_in),
                "slippageBps": int(self.config.max_slippage_percent * 100)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(quote_url, params=params) as response:
                    if response.status != 200:
                        logger.error("Failed to get quote for closing position")
                        return
                    
                    quote_data = await response.json()
                    
                    # Get transaction data
                    swap_url = f"{JUPITER_API_BASE}/swap"
                    swap_data = {
                        "quoteResponse": quote_data,
                        "userPublicKey": self.wallet.public_key,
                        "wrapUnwrapSOL": True
                    }
                    
                    async with session.post(swap_url, json=swap_data) as swap_response:
                        if swap_response.status != 200:
                            logger.error("Failed to prepare closing transaction")
                            return
                        
                        swap_result = await swap_response.json()
                        
                        # Sign and send transaction
                        tx = Transaction.deserialize(base58.b58decode(swap_result["swapTransaction"]))
                        signed_tx = await self.wallet.sign_transaction(tx)
                        
                        # Send transaction
                        result = await self.solana.send_transaction(signed_tx)
                        signature = result.value
                        
                        # Update trade record
                        trade.status = "closed"
                        trade.transaction_signature = signature
                        
                        logger.info(f"Position closed: {trade}, Reason: {reason}")
                        
        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
    
    async def start_trading(self):
        """Start the trading bot."""
        if self.is_running:
            logger.warning("Trading bot is already running")
            return
        
        self.is_running = True
        self._trading_task = asyncio.create_task(self._trading_loop())
        logger.info("Trading bot started")
    
    async def stop_trading(self):
        """Stop the trading bot."""
        if not self.is_running:
            logger.warning("Trading bot is not running")
            return
        
        self.is_running = False
        if self._trading_task:
            self._trading_task.cancel()
            try:
                await self._trading_task
            except asyncio.CancelledError:
                pass
        logger.info("Trading bot stopped")
    
    async def _trading_loop(self):
        """Main trading loop."""
        while self.is_running:
            try:
                # Check if we can make more trades today
                current_date = datetime.now().date()
                if current_date > self.last_trade_reset:
                    self.trades_today = 0
                    self.last_trade_reset = current_date
                
                if self.trades_today >= self.config.max_trades_per_day:
                    logger.info("Maximum daily trades reached")
                    await asyncio.sleep(60)  # Check again in a minute
                    continue
                
                # Check active positions
                await self._check_positions()
                
                # Look for new trading opportunities
                await self._find_trading_opportunities()
                
                await asyncio.sleep(10)  # Wait before next iteration
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {str(e)}")
                logger.debug(traceback.format_exc())
                await asyncio.sleep(30)  # Wait longer on error
    
    async def _check_positions(self):
        """Check and manage open positions."""
        for trade in self.get_active_trades():
            try:
                current_price = await self._get_token_price(trade.token_address)
                if current_price is None:
                    continue
                
                # Check stop loss
                if (trade.stop_loss_sol and 
                    current_price <= trade.stop_loss_sol):
                    await self._close_position(trade, 'stop_loss')
                
                # Check take profit
                elif (trade.take_profit_sol and 
                      current_price >= trade.take_profit_sol):
                    await self._close_position(trade, 'take_profit')
                
            except Exception as e:
                logger.error(f"Error checking position {trade.token_address}: {str(e)}")
    
    async def _find_trading_opportunities(self):
        """Find new trading opportunities."""
        try:
            # Get trending tokens from Jupiter/Solscan
            trending_tokens = await self._get_trending_tokens()
            
            for token in trending_tokens:
                # Analyze token for potential trade
                if await self._analyze_token(token):
                    # Execute trade if analysis is positive
                    await self._execute_trade(token)
        
        except Exception as e:
            logger.error(f"Error finding trading opportunities: {str(e)}")
    
    def get_active_trades(self) -> List[Trade]:
        """Get list of active trades."""
        return [trade for trade in self.active_trades if trade.status == 'open']
    
    def get_trade_history(self) -> List[Trade]:
        """Get list of historical trades."""
        return [trade for trade in self.active_trades if trade.status != 'open']
    
    def get_trading_stats(self) -> Dict[str, float]:
        """Get trading statistics."""
        active_trades = self.get_active_trades()
        total_value_sol = sum(trade.entry_price_sol * trade.quantity_tokens for trade in active_trades)
        
        return {
            'total_trades': len(self.active_trades),
            'active_trades': len(active_trades),
            'total_value_sol': total_value_sol,
            'sol_balance': self.get_sol_balance(),
            'trades_today': self.trades_today
        }
