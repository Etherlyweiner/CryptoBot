"""Trading bot implementation."""

import logging
import asyncio
import logging.config
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from bot.wallet.phantom_integration import PhantomWalletManager
from bot.api.helius_client import HeliusClient
from bot.api.jupiter_client import JupiterClient
from .trade_logger import TradeLogger
from .websocket_server import WebSocketServer
from .price_monitor import PriceMonitor
from .strategy import TradingStrategy
from .risk_manager import RiskManager

# Load logging configuration
with open('config/logging_config.yaml', 'r') as f:
    logging_config = yaml.safe_load(f)
logging.config.dictConfig(logging_config)

logger = logging.getLogger('cryptobot.trading')

class TradingBot:
    """Trading bot implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize trading bot.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.running = False
        self.last_trade_time = None
        self.trade_count = 0
        
        # Initialize wallet manager
        self.wallet_manager = PhantomWalletManager(config)
        
        # Initialize API clients
        helius_config = config.get('api_keys', {}).get('helius', {})
        if not helius_config or not helius_config.get('key'):
            raise ValueError("Helius API key not found in config")
            
        # Use staked RPC URL by default, fallback to standard RPC
        rpc_url = helius_config.get('staked_rpc') or helius_config.get('rpc_url')
        if not rpc_url:
            raise ValueError("No valid Helius RPC URL found in config")
            
        self.helius = HeliusClient(
            api_key=helius_config['key'],
            rpc_url=rpc_url
        )
        
        # Initialize Jupiter DEX client
        self.jupiter = JupiterClient(rpc_url)
        
        # Trading settings
        self.settings = config.get('trading', {})
        self.min_sol_balance = Decimal(str(self.settings.get('min_sol_balance', '0.05')))
        self.max_slippage = Decimal(str(self.settings.get('max_slippage', '1.0')))  # 1%
        self.position_size = Decimal(str(self.settings.get('position_size', '0.1')))  # 0.1 SOL
        self.cooldown_minutes = int(self.settings.get('cooldown_minutes', 60))
        self.priority_fee = int(self.settings.get('priority_fee', 10000))  # 0.00001 SOL
        
        # Initialize trade logger
        self.trade_logger = TradeLogger()
        
        # Initialize WebSocket server
        self.ws_server = WebSocketServer()
        
        # Initialize price monitor
        self.price_monitor = None
        
        # Initialize strategy
        self.strategy = None
        
        # Initialize risk manager
        self.risk_manager = None
        
        # Load strategy settings
        self.strategy_config = config.get('strategy', {})
        
        # Load risk settings
        self.risk_config = config.get('risk', {})
            
    async def initialize(self) -> Tuple[bool, str]:
        """Initialize the trading bot.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            logger.info("Initializing trading bot...")
            
            # Initialize wallet with retries
            logger.info("Initializing wallet...")
            max_retries = 3
            wallet_success = False
            wallet_message = ""
            
            for attempt in range(max_retries):
                try:
                    wallet_success, wallet_message = await self.wallet_manager.connect()
                    if wallet_success:
                        break
                    logger.warning(f"Wallet initialization attempt {attempt + 1}/{max_retries} failed: {wallet_message}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                except Exception as e:
                    logger.warning(f"Wallet initialization attempt {attempt + 1}/{max_retries} failed with error: {str(e)}")
                    wallet_message = str(e)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
            
            if not wallet_success:
                logger.error(f"Wallet initialization failed after {max_retries} attempts: {wallet_message}")
                return False, f"Wallet initialization failed: {wallet_message}"
                
            # Get SOL balance with retries
            balance_success = False
            balance = 0
            balance_error = ""
            
            for attempt in range(max_retries):
                try:
                    balance_success, balance_result = await self.wallet_manager.get_sol_balance()
                    if balance_success:
                        balance = balance_result
                        break
                    logger.warning(f"Balance check attempt {attempt + 1}/{max_retries} failed: {balance_result}")
                    balance_error = balance_result
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                except Exception as e:
                    logger.warning(f"Balance check attempt {attempt + 1}/{max_retries} failed with error: {str(e)}")
                    balance_error = str(e)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
            
            if not balance_success:
                logger.error(f"Failed to get SOL balance after {max_retries} attempts: {balance_error}")
                return False, f"Failed to get SOL balance: {balance_error}"
                
            if balance < self.min_sol_balance:
                logger.error(f"Insufficient SOL balance: {balance:.4f} SOL (minimum required: {self.min_sol_balance} SOL)")
                return False, f"Insufficient SOL balance: {balance:.4f} SOL (minimum required: {self.min_sol_balance} SOL)"
                
            logger.info(f"Wallet initialized with {balance:.4f} SOL")
            
            # Test API connections
            if not await self._test_api_connections():
                logger.error("API connection tests failed")
                return False, "API connection tests failed"
                
            # Initialize price monitor
            self.price_monitor = PriceMonitor(self.jupiter)
            
            # Initialize strategy
            self.strategy = TradingStrategy(self.price_monitor, self.strategy_config)
            
            # Initialize risk manager
            self.risk_manager = RiskManager(self.risk_config)
            
            logger.info("Trading bot initialized successfully")
            return True, "Initialized successfully"
            
        except Exception as e:
            logger.exception(f"Error initializing trading bot: {str(e)}")
            return False, str(e)
            
    async def _test_api_connections(self) -> bool:
        """Test connections to all APIs.
        
        Returns:
            True if all critical connections are successful
        """
        try:
            # Test Helius RPC connection
            network = await self.helius.get_network_version()
            if not network:
                logger.error("Helius RPC connection test failed")
                return False
                
            # Test Jupiter API connection with increased timeout
            for attempt in range(3):
                if await self.jupiter.test_connection():
                    break
                if attempt < 2:  # Don't sleep on last attempt
                    await asyncio.sleep(2 ** attempt)
            else:
                logger.error("Jupiter API connection test failed after 3 attempts")
                return False
                
            # Initialize token list
            tokens = await self.jupiter.get_token_list(force_refresh=True)
            if not tokens:
                logger.error("Failed to initialize token list")
                return False
                
            # Verify WSOL token is available
            wsol = self.jupiter.find_token("WSOL")
            if not wsol:
                logger.error("Could not find WSOL token in token list")
                return False
                
            logger.info("All API connection tests passed")
            return True
            
        except Exception as e:
            logger.exception(f"API connection tests failed: {str(e)}")
            return False
            
    async def start(self):
        """Start the trading bot."""
        try:
            # Start price monitor
            if self.price_monitor:
                await self.price_monitor.start()
                
            # Start WebSocket server
            await self.ws_server.start()
            
            # Initialize bot with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    success, message = await self.initialize()
                    if success:
                        break
                    logger.warning(f"Bot initialization attempt {attempt + 1}/{max_retries} failed: {message}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                except Exception as e:
                    logger.warning(f"Bot initialization attempt {attempt + 1}/{max_retries} failed with error: {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
            
            if not success:
                logger.error(f"Bot initialization failed after {max_retries} attempts: {message}")
                return
            
            self.running = True
            logger.info("Trading bot started successfully")
            await self._trading_loop()
            
        except Exception as e:
            logger.exception(f"Error starting trading bot: {str(e)}")
            await self.stop()
            
    async def stop(self):
        """Stop the trading bot."""
        self.running = False
        
        # Stop price monitor
        if self.price_monitor:
            await self.price_monitor.stop()
            
        # Stop WebSocket server
        await self.ws_server.stop()
        
    async def _log_and_broadcast_trade(self, trade_data):
        """Log trade and broadcast to WebSocket clients."""
        # Log trade
        if self.trade_logger.log_trade(trade_data):
            # Get updated performance metrics
            metrics = self.trade_logger.get_performance_metrics()
            
            # Broadcast trade and metrics
            await self.ws_server.broadcast_update('trade', trade_data)
            await self.ws_server.broadcast_update('performance', metrics)
            
    async def _broadcast_price_updates(self):
        """Broadcast price updates to WebSocket clients."""
        if not self.price_monitor:
            return
            
        prices = self.price_monitor.get_all_prices()
        for token_address, price_data in prices.items():
            await self.ws_server.broadcast_update('price', {
                'token': token_address,
                'price': price_data['price'],
                'priceChange': price_data['priceChange'],
                'timestamp': price_data['timestamp']
            })
            
    async def _execute_trade(self, opportunity: Dict, position_size: Decimal) -> bool:
        """Execute a trade.
        
        Args:
            opportunity: Trading opportunity
            position_size: Position size in SOL
            
        Returns:
            bool: True if trade was successful
        """
        try:
            # Check risk limits
            can_trade, reason = self.risk_manager.can_open_position(
                opportunity['token'],
                position_size,
                self.wallet_manager.get_sol_balance()
            )
            
            if not can_trade:
                logger.warning(f"Trade rejected by risk manager: {reason}")
                return False
                
            # Prepare trade
            token_address = opportunity['token']
            trade_type = opportunity['type']
            
            # Calculate amounts
            amount_in = position_size * Decimal('1000000000')  # Convert to lamports
            
            # Get quote
            quote = await self.jupiter.get_quote(
                input_mint=token_address if trade_type == 'sell' else 'So11111111111111111111111111111111111111112',
                output_mint=token_address if trade_type == 'buy' else 'So11111111111111111111111111111111111111112',
                amount=int(amount_in),
                slippage_bps=100  # 1% slippage
            )
            
            if not quote:
                logger.error("Failed to get quote")
                return False
                
            # Execute swap
            success = await self.jupiter.swap(
                wallet_pubkey=self.wallet_manager.public_key,
                quote=quote
            )
            
            if success:
                # Record position
                self.risk_manager.open_position(
                    opportunity['token'],
                    Decimal(str(opportunity['price'])),
                    position_size
                )
                
                # Log trade
                trade_data = {
                    'timestamp': datetime.now().isoformat(),
                    'type': trade_type,
                    'token': token_address,
                    'amount': float(position_size),
                    'price': opportunity['price'],
                    'slippage': 1.0
                }
                await self._log_and_broadcast_trade(trade_data)
                
                # Update last trade time
                self.last_trade_time = datetime.now()
                
                logger.info(f"Trade executed: {trade_type} {position_size} SOL worth of {token_address}")
                return True
                
            else:
                logger.error("Trade execution failed")
                return False
                
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return False
            
    async def _update_risk_metrics(self):
        """Update and broadcast risk metrics."""
        try:
            # Update position PnLs
            if self.price_monitor and self.risk_manager:
                prices = self.price_monitor.get_all_prices()
                for token, price_data in prices.items():
                    if token in self.risk_manager.open_positions:
                        self.risk_manager.update_position_pnl(
                            token,
                            Decimal(str(price_data['price']))
                        )
                        
            # Get current metrics
            metrics = self.risk_manager.get_position_risk_metrics()
            
            # Broadcast metrics
            await self.ws_server.broadcast_update('risk', metrics)
            
        except Exception as e:
            logger.error(f"Error updating risk metrics: {str(e)}")
            
    async def _trading_loop(self):
        """Main trading loop."""
        try:
            while self.running:
                try:
                    # Check if we can trade (cooldown and balance)
                    if self.last_trade_time:
                        elapsed = (datetime.now() - self.last_trade_time).total_seconds() / 60
                        if elapsed < self.cooldown_minutes:
                            logger.debug(f"Cooling down, {self.cooldown_minutes - elapsed:.1f} minutes remaining")
                            await asyncio.sleep(60)  # Check again in a minute
                            continue
                            
                    # Check SOL balance
                    success, balance = await self.wallet_manager.get_sol_balance()
                    if not success or balance < self.min_sol_balance:
                        logger.warning(f"Insufficient SOL balance: {balance:.4f} SOL")
                        await asyncio.sleep(300)  # Check again in 5 minutes
                        continue
                        
                    # Update token prices
                    if self.price_monitor:
                        # Find trading opportunities
                        opportunities = self.strategy.find_trading_opportunities()
                        
                        # Execute best opportunity if available
                        if opportunities:
                            best_opportunity = opportunities[0]
                            position_size = self.strategy.calculate_position_size(
                                best_opportunity,
                                Decimal(str(balance))
                            )
                            
                            if position_size > 0:
                                logger.info(f"Found trading opportunity: {best_opportunity}")
                                success = await self._execute_trade(best_opportunity, position_size)
                                if success:
                                    await asyncio.sleep(self.cooldown_minutes * 60)  # Wait for cooldown
                                    continue
                                    
                        # Broadcast price updates
                        await self._broadcast_price_updates()
                        
                    # Update risk metrics
                    await self._update_risk_metrics()
                    
                    # Sleep to prevent CPU spinning
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error in trading loop: {str(e)}")
                    await asyncio.sleep(60)  # Wait before retrying
                    
        except Exception as e:
            logger.exception(f"Fatal error in trading loop: {str(e)}")
            await self.stop()
