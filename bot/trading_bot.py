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
            logger.info("Testing API connections...")
            
            # Test Helius API connection with retries
            logger.info("Testing Helius API connection...")
            helius_success = False
            for attempt in range(3):
                try:
                    async with self.helius as client:
                        if await client.test_connection():
                            helius_success = True
                            logger.info("Helius API connection successful")
                            break
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                except Exception as e:
                    logger.warning(f"Helius connection attempt {attempt + 1}/3 failed: {str(e)}")
                    if attempt < 2:  # Don't sleep on last attempt
                        await asyncio.sleep(2 ** attempt)
                        
            if not helius_success:
                logger.error("Helius connection test failed")
                return False
                
            # Test Jupiter API connection
            try:
                async with self.jupiter as jupiter:
                    tokens = await jupiter.get_token_list()
                    if tokens:
                        logger.info("Jupiter API connection successful")
                    else:
                        logger.error("Jupiter token list empty")
                        return False
            except Exception as e:
                logger.error(f"Jupiter connection failed: {str(e)}")
                return False
                    
            return True
            
        except Exception as e:
            logger.exception(f"Error testing API connections: {str(e)}")
            return False
            
    async def start(self):
        """Start the trading bot."""
        try:
            logger.info("Starting trading bot...")
            
            # Initialize bot
            success, message = await self.initialize()
            if not success:
                logger.error(f"Bot initialization failed: {message}")
                return
            
            self.running = True
            logger.info("Trading bot started successfully")
            await self._trading_loop()
            
        except Exception as e:
            logger.exception(f"Error starting trading bot: {str(e)}")
            await self.stop()
            
    async def stop(self):
        """Stop the trading bot."""
        try:
            logger.info("Stopping trading bot...")
            self.running = False
            
            # Close API connections
            if hasattr(self, 'helius') and self.helius:
                await self.helius._close_session()
                
            if hasattr(self, 'jupiter') and self.jupiter:
                await self.jupiter._close_session()
                
            logger.info("Trading bot stopped")
            
        except Exception as e:
            logger.exception(f"Error stopping trading bot: {str(e)}")
            
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
                        
                    # Calculate position size in lamports (1 SOL = 1e9 lamports)
                    position_lamports = int(self.position_size * Decimal('1000000000'))
                    
                    # Get token list from Jupiter
                    async with self.jupiter as jupiter:
                        tokens = await jupiter.get_token_list()
                        if not tokens:
                            logger.error("Failed to get token list")
                            await asyncio.sleep(60)
                            continue
                            
                        # Find WSOL token (wrapped SOL)
                        wsol_token = next((t for t in tokens if t.get('symbol') == 'WSOL'), None)
                        if not wsol_token:
                            logger.error("Could not find WSOL token")
                            await asyncio.sleep(60)
                            continue
                            
                        # TODO: Implement token selection strategy
                        # For now, we'll just log that we're ready to trade
                        logger.info(f"Ready to trade {self.position_size} SOL")
                        logger.debug(f"Available tokens: {len(tokens)}")
                        
                        # Sleep to prevent CPU spinning
                        await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.exception(f"Error in trading loop: {str(e)}")
                    await asyncio.sleep(5)  # Wait before retrying
                    
        except asyncio.CancelledError:
            logger.info("Trading loop cancelled")
            await self.stop()
            
        except Exception as e:
            logger.exception(f"Fatal error in trading loop: {str(e)}")
            await self.stop()
