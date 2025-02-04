"""Trading bot implementation."""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from bot.wallet.phantom_integration import PhantomWalletManager
from bot.api.helius_client import HeliusClient
from bot.api.solscan_client import SolscanClient

logger = logging.getLogger(__name__)

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
        
        solscan_config = config.get('api_keys', {}).get('solscan', {})
        if solscan_config and solscan_config.get('key'):
            self.solscan = SolscanClient(solscan_config.get('key'))
        else:
            self.solscan = None
            logger.warning("Solscan API key not found, some features will be limited")
            
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
                
            # Test Solscan connection (non-critical)
            if self.solscan:
                try:
                    async with self.solscan as client:
                        if not await client.test_connection():
                            logger.warning("Solscan connection test failed")
                        else:
                            logger.info("Solscan API connection successful")
                except Exception as e:
                    logger.warning(f"Solscan connection failed: {str(e)}")
                    
            return True
            
        except Exception as e:
            logger.error(f"Error testing API connections: {str(e)}")
            return False
            
    async def start(self):
        """Start the trading bot."""
        try:
            logger.info("Starting trading bot...")
            
            # Initialize wallet
            logger.info("Initializing wallet...")
            wallet_success, wallet_message = await self.wallet_manager.connect()
            if not wallet_success:
                logger.error(f"Wallet initialization failed: {wallet_message}")
                return
                
            logger.info("Wallet initialized successfully")
            
            # Test API connections
            logger.info("Testing API connections...")
            if not await self._test_api_connections():
                logger.error("API connection tests failed")
                await self.stop()
                return
                
            self.running = True
            logger.info("Trading bot started successfully")
            await self._trading_loop()
            
        except Exception as e:
            logger.error(f"Error starting trading bot: {str(e)}")
            await self.stop()
            
    async def stop(self):
        """Stop the trading bot."""
        try:
            logger.info("Stopping trading bot...")
            self.running = False
            
            # Close API connections
            if hasattr(self, 'helius') and self.helius:
                await self.helius._close_session()
                
            if hasattr(self, 'solscan') and self.solscan:
                await self.solscan._close_session()
                
            logger.info("Trading bot stopped")
            
        except Exception as e:
            logger.error(f"Error stopping trading bot: {str(e)}")
            
    async def _trading_loop(self):
        """Main trading loop."""
        try:
            while self.running:
                try:
                    # TODO: Implement trading strategy
                    await asyncio.sleep(1)  # Prevent CPU spinning
                    
                except Exception as e:
                    logger.error(f"Error in trading loop: {str(e)}")
                    await asyncio.sleep(5)  # Wait before retrying
                    
        except asyncio.CancelledError:
            logger.info("Trading loop cancelled")
            await self.stop()
            
        except Exception as e:
            logger.error(f"Fatal error in trading loop: {str(e)}")
            await self.stop()
