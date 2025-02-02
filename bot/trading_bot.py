"""Main trading bot implementation."""

import asyncio
import logging
from typing import Dict, List, Optional
from decimal import Decimal
import json
from datetime import datetime
from dataclasses import dataclass, field
import aiohttp
import traceback

from bot.wallet.phantom_integration import PhantomWalletManager
from cache_manager import cache_manager, market_cache
from metrics_collector import metrics
from system_health import health_checker
from security_manager import security_manager

logger = logging.getLogger('TradingBot')

@dataclass
class Trade:
    """Represents an active trade."""
    symbol: str
    entry_price: float
    quantity: float
    side: str  # 'buy' or 'sell'
    timestamp: datetime = field(default_factory=datetime.now)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: str = 'open'  # 'open', 'closed', 'cancelled'

@dataclass
class TradingConfig:
    """Trading configuration."""
    base_currency: str
    quote_currency: str
    position_size: float
    stop_loss: float
    take_profit: float
    max_slippage: float
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
        self.active_trades: List[Trade] = []  # List to track active trades
        self.trades_today = 0
        self.last_trade_reset = datetime.now().date()
        self._trading_task = None
        self.MAX_RETRIES = 5  # Maximum number of retries for failed trades
        self.RETRY_DELAY = 5  # Delay in seconds between retries
        
        # Initialize metrics
        self.trade_count = metrics.trade_count
        self.position_value = metrics.position_value
        self.pnl = metrics.pnl
        
        # Update max slippage to 5%
        self.config.max_slippage = 0.05
        
        # Connect wallet if not already connected
        if not self.wallet.is_connected():
            success, message = self.wallet.connect()
            if not success:
                logger.error(f"Failed to connect wallet: {message}")
                raise RuntimeError(f"Failed to connect wallet: {message}")
        
        logger.debug("TradingBot initialized with config: %s", config)
    
    def get_balance(self) -> float:
        """Get wallet balance."""
        try:
            return self.wallet.get_balance()
        except Exception as e:
            logger.error(f"Failed to get balance: {str(e)}")
            return 0.0
    
    def get_active_trades(self) -> List[Trade]:
        """Get list of active trades."""
        return [trade for trade in self.active_trades if trade.status == 'open']
    
    def get_trade_history(self) -> List[Trade]:
        """Get list of historical trades."""
        return [trade for trade in self.active_trades if trade.status != 'open']
    
    def get_trading_stats(self) -> Dict[str, int]:
        """Get trading statistics."""
        return {
            'total_trades': len(self.active_trades),
            'active_trades': len(self.get_active_trades()),
            'closed_trades': len([t for t in self.active_trades if t.status == 'closed']),
            'cancelled_trades': len([t for t in self.active_trades if t.status == 'cancelled']),
            'trades_today': self.trades_today
        }
    
    async def _check_connections(self) -> bool:
        """Check all necessary connections."""
        try:
            # Check wallet connection
            if not self.wallet.is_connected():
                logger.error("Wallet is not connected")
                return False

            # Check wallet balance
            balance = self.wallet.get_balance()
            if balance <= 0:
                logger.error(f"Insufficient wallet balance: {balance} SOL")
                return False

            # Test market data connection
            test_symbol = "BONK"  # Use BONK as test symbol
            market_data = await self._fetch_market_data(test_symbol)
            if not market_data:
                logger.error("Failed to fetch market data")
                return False

            logger.info("All connections checked and working")
            return True

        except Exception as e:
            logger.error(f"Connection check failed: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    async def start(self):
        """Start the trading bot."""
        try:
            logger.info("Starting trading bot...")
            
            # Check connections before starting
            if not await self._check_connections():
                logger.error("Failed to start trading bot - connection check failed")
                return False

            self.is_running = True
            self._trading_task = asyncio.create_task(self._trading_loop())
            logger.info("Trading bot started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start trading bot: {str(e)}")
            logger.error(traceback.format_exc())
            self.is_running = False
            return False

    def stop(self):
        """Stop the trading bot."""
        if self.is_running:
            self.is_running = False
            if self._trading_task:
                self._trading_task.cancel()
            logger.info("Trading bot stopped")
    
    async def _execute_trade(self, trade: Trade, retries: int = 0) -> bool:
        """Execute a trade with retry logic."""
        try:
            # Your existing trade execution logic here
            # This is a placeholder - implement actual trade execution
            logger.info(f"Attempting to execute trade: {trade}")
            
            # Simulate trade execution (replace with actual implementation)
            success = await self._place_order(trade)
            
            if success:
                logger.info(f"Trade executed successfully: {trade}")
                return True
            
            if retries < self.MAX_RETRIES:
                logger.warning(f"Trade failed, retrying ({retries + 1}/{self.MAX_RETRIES})")
                await asyncio.sleep(self.RETRY_DELAY)
                return await self._execute_trade(trade, retries + 1)
            else:
                logger.error(f"Trade failed after {self.MAX_RETRIES} attempts")
                return False
                
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            if retries < self.MAX_RETRIES:
                logger.warning(f"Retrying trade after error ({retries + 1}/{self.MAX_RETRIES})")
                await asyncio.sleep(self.RETRY_DELAY)
                return await self._execute_trade(trade, retries + 1)
            return False

    async def _place_order(self, trade: Trade) -> bool:
        """Place an order with the specified slippage tolerance."""
        try:
            # Your order placement logic here
            # This is a placeholder - implement actual order placement
            
            # Example implementation:
            # 1. Calculate price with slippage
            slippage_factor = 1 + (self.config.max_slippage if trade.side == 'buy' else -self.config.max_slippage)
            adjusted_price = trade.entry_price * slippage_factor
            
            # 2. Place the order
            logger.info(f"Placing {trade.side} order for {trade.quantity} {trade.symbol} at {adjusted_price}")
            
            # 3. Wait for confirmation
            # Add your order confirmation logic here
            
            return True  # Return True if order was placed successfully
            
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            return False

    def _get_token_mint(self, symbol: str) -> str:
        """Get token mint address for a symbol."""
        # Common Solana token addresses
        token_addresses = {
            'BONK': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
            'SAMO': '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU',
            'BOME': '5jFnsfx36DyGk8uVGrbXnVUMTsBkPXGpx6e69BiGFzko',
            'MYRO': 'HhJpBhRRn4g56VsyLuT8DL5Bv31HkXqsrahTTUCZeZg4',
            'WIF': 'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm'
        }
        return token_addresses.get(symbol)

    async def _fetch_market_data(self, symbol: str) -> Optional[Dict]:
        """Fetch market data for a symbol."""
        try:
            # Get token mint address
            token_mint = self._get_token_mint(symbol)
            if not token_mint:
                logger.error(f"No mint address found for {symbol}")
                return None

            # Use Jupiter API to get market data
            url = f"https://price.jup.ag/v4/price?ids={token_mint}"
            logger.debug(f"Fetching market data for {symbol} from {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"Received data for {symbol}: {json.dumps(data, indent=2)}")
                        if data and "data" in data and token_mint in data["data"]:
                            market_data = data["data"][token_mint]
                            market_data["symbol"] = symbol  # Add symbol for reference
                            logger.info(f"Market data for {symbol}: Price=${market_data.get('price', 'N/A')}, 24h Change: {market_data.get('price_change_24h', 'N/A')}%")
                            return market_data
                    else:
                        logger.error(f"Failed to fetch data for {symbol}. Status: {response.status}")
            return None
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    async def _analyze_token(self, symbol: str) -> Optional[Trade]:
        """Analyze a token for trading opportunities."""
        try:
            logger.debug(f"Analyzing token: {symbol}")
            market_data = await self._fetch_market_data(symbol)
            
            if not market_data:
                logger.warning(f"No market data available for {symbol}")
                return None

            current_price = float(market_data.get("price", 0))
            if current_price <= 0:
                logger.warning(f"Invalid price for {symbol}: {current_price}")
                return None

            # Get recent price history
            price_change = float(market_data.get("price_change_24h", 0))
            volume = float(market_data.get("volume_24h", 0))
            
            logger.info(f"Analysis for {symbol}:")
            logger.info(f"  - Current Price: ${current_price:.6f}")
            logger.info(f"  - 24h Price Change: {price_change:.2f}%")
            logger.info(f"  - 24h Volume: {volume:.2f} SOL")

            # Get wallet balance
            wallet_balance = self.wallet.get_balance()
            if wallet_balance <= 0:
                logger.warning(f"Insufficient wallet balance: {wallet_balance} SOL")
                return None
            
            logger.info(f"Wallet balance: {wallet_balance:.4f} SOL")

            # Trading strategy conditions
            strategy_conditions = {
                "price_drop": price_change < -5,
                "volume_sufficient": volume > 1000,
                "balance_sufficient": wallet_balance > 0.1  # Minimum 0.1 SOL required
            }
            
            logger.info(f"Strategy conditions for {symbol}:")
            logger.info(f"  - Price Drop > 5%: {strategy_conditions['price_drop']} ({price_change:.2f}%)")
            logger.info(f"  - Volume > 1000 SOL: {strategy_conditions['volume_sufficient']} ({volume:.2f} SOL)")
            logger.info(f"  - Balance > 0.1 SOL: {strategy_conditions['balance_sufficient']} ({wallet_balance:.4f} SOL)")

            if all(strategy_conditions.values()):
                # Calculate position size based on wallet balance
                position_size = wallet_balance * self.config.position_size
                
                logger.info(f"Creating trade for {symbol}:")
                logger.info(f"  - Wallet Balance: {wallet_balance:.4f} SOL")
                logger.info(f"  - Position Size: {position_size:.4f} SOL")

                # Create trade object
                trade = Trade(
                    symbol=symbol,
                    entry_price=current_price,
                    quantity=position_size / current_price,
                    side="buy",
                    stop_loss=current_price * (1 - self.config.stop_loss),
                    take_profit=current_price * (1 + self.config.take_profit)
                )
                
                logger.info(f"Trade details:")
                logger.info(f"  - Quantity: {trade.quantity:.2f}")
                logger.info(f"  - Entry Price: ${trade.entry_price:.6f}")
                logger.info(f"  - Stop Loss: ${trade.stop_loss:.6f}")
                logger.info(f"  - Take Profit: ${trade.take_profit:.6f}")
                
                return trade
            else:
                conditions_not_met = [k for k, v in strategy_conditions.items() if not v]
                logger.debug(f"No trading opportunity for {symbol} - conditions not met: {conditions_not_met}")
                return None

        except Exception as e:
            logger.error(f"Error analyzing token {symbol}: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    async def _find_trading_opportunities(self) -> List[Trade]:
        """Find new trading opportunities."""
        try:
            logger.info("Starting trading opportunity search...")
            opportunities = []
            
            # List of tokens to monitor (customize as needed)
            tokens_to_monitor = [
                "BONK", "SAMO", "BOME", "MYRO", "WIF"  # Popular Solana memecoins
            ]
            
            logger.info(f"Monitoring tokens: {', '.join(tokens_to_monitor)}")
            
            # Analyze each token
            for token in tokens_to_monitor:
                try:
                    logger.debug(f"Analyzing {token}...")
                    trade = await self._analyze_token(token)
                    if trade:
                        logger.info(f"Found opportunity for {token}")
                        opportunities.append(trade)
                    else:
                        logger.debug(f"No opportunity found for {token}")
                except Exception as e:
                    logger.error(f"Error analyzing {token}: {str(e)}")
                    logger.error(traceback.format_exc())
                    continue
                
                # Add small delay between API calls
                await asyncio.sleep(0.5)
            
            if opportunities:
                logger.info(f"Found {len(opportunities)} trading opportunities")
            else:
                logger.info("No trading opportunities found in this iteration")
            return opportunities

        except Exception as e:
            logger.error(f"Error finding trading opportunities: {str(e)}")
            logger.error(traceback.format_exc())
            return []

    async def _update_trade(self, trade: Trade):
        """Update a single trade."""
        try:
            if trade.status != "open":
                return

            logger.debug(f"Updating trade for {trade.symbol}")
            
            # Get current price
            market_data = await self._fetch_market_data(trade.symbol)
            if not market_data:
                logger.warning(f"Could not get market data for {trade.symbol}")
                return

            current_price = float(market_data.get("price", 0))
            if current_price <= 0:
                logger.warning(f"Invalid current price for {trade.symbol}: {current_price}")
                return

            logger.info(f"Trade status for {trade.symbol}:")
            logger.info(f"  - Entry Price: ${trade.entry_price}")
            logger.info(f"  - Current Price: ${current_price}")
            logger.info(f"  - Stop Loss: ${trade.stop_loss}")
            logger.info(f"  - Take Profit: ${trade.take_profit}")

            # Check stop loss
            if current_price <= trade.stop_loss:
                logger.info(f"Stop loss triggered for {trade.symbol} at ${current_price}")
                trade.status = "closed"
                return

            # Check take profit
            if current_price >= trade.take_profit:
                logger.info(f"Take profit triggered for {trade.symbol} at ${current_price}")
                trade.status = "closed"
                return

            # Calculate current P&L
            pnl_percent = ((current_price - trade.entry_price) / trade.entry_price) * 100
            logger.info(f"Current P&L for {trade.symbol}: {pnl_percent:.2f}%")

        except Exception as e:
            logger.error(f"Error updating trade {trade}: {str(e)}")
            logger.error(traceback.format_exc())

    async def _trading_loop(self):
        """Main trading loop."""
        while self.is_running:
            try:
                # Check connections periodically
                if not await self._check_connections():
                    logger.error("Connection check failed, pausing trading")
                    await asyncio.sleep(60)  # Wait a minute before retrying
                    continue

                # Reset daily trade counter if needed
                today = datetime.now().date()
                if today > self.last_trade_reset:
                    self.trades_today = 0
                    self.last_trade_reset = today
                
                # Check if we can make more trades today
                if self.trades_today >= self.config.max_trades_per_day:
                    logger.info("Daily trade limit reached")
                    await asyncio.sleep(60)  # Check again in a minute
                    continue
                
                # Check if we have too many positions open
                if len(self.get_active_trades()) >= self.config.max_positions:
                    logger.info("Maximum positions reached")
                    await asyncio.sleep(60)  # Check again in a minute
                    continue

                # Get wallet balance
                balance = self.wallet.get_balance()
                if balance <= 0.1:  # Minimum 0.1 SOL required
                    logger.warning(f"Insufficient balance: {balance} SOL")
                    await asyncio.sleep(60)
                    continue
                
                # Update active trades
                active_trades = self.get_active_trades()
                logger.info(f"Updating {len(active_trades)} active trades")
                for trade in active_trades:
                    await self._update_trade(trade)
                
                # Look for new trading opportunities
                logger.info("Searching for trading opportunities...")
                opportunities = await self._find_trading_opportunities()
                
                if opportunities:
                    logger.info(f"Found {len(opportunities)} trading opportunities")
                    for opp in opportunities:
                        if await self._execute_trade(opp):
                            self.active_trades.append(opp)
                            self.trades_today += 1
                            logger.info(f"Successfully executed trade for {opp.symbol}")
                        else:
                            logger.error(f"Failed to execute trade for {opp.symbol}")
                else:
                    logger.debug("No trading opportunities found")
                
                # Sleep before next iteration
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in trading loop: {str(e)}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(60)  # Wait longer on error
