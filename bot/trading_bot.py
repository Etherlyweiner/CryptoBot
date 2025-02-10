"""CryptoBot main class."""

import logging
import asyncio
from typing import Dict, Any, Optional
import yaml

from .api import BirdeyeClient, JupiterClient
from .strategy import StrategyExecutor
from .risk import RiskManager
from .performance import PerformanceAnalytics
from .wallet import PhantomWalletManager

logger = logging.getLogger(__name__)

class CryptoBot:
    """Main trading bot class."""
    
    def __init__(self, config_path: str):
        """Initialize CryptoBot.
        
        Args:
            config_path: Path to config.yaml
        """
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        # Initialize components
        self.birdeye = BirdeyeClient(self.config)
        self.jupiter = JupiterClient(self.config)
        self.wallet = PhantomWalletManager(self.config)
        self.strategy = StrategyExecutor(self)
        self.risk = RiskManager(self)
        self.analytics = PerformanceAnalytics(self)
        
        # State
        self.is_running = False
        self.last_error: Optional[str] = None
        
    async def initialize(self):
        """Initialize all components."""
        try:
            logger.info("Initializing CryptoBot...")
            
            # Initialize API clients
            await self.birdeye.initialize()
            await self.jupiter.initialize()
            
            # Initialize wallet
            await self.wallet.initialize()
            if not await self.wallet.is_connected():
                raise Exception("Wallet not connected")
                
            # Initialize trading components
            await self.strategy.initialize()
            await self.risk.initialize()
            await self.analytics.initialize()
            
            logger.info("CryptoBot initialized successfully")
            
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to initialize CryptoBot: {str(e)}")
            raise
            
    async def start(self):
        """Start the trading bot."""
        try:
            if self.is_running:
                logger.warning("CryptoBot is already running")
                return
                
            logger.info("Starting CryptoBot...")
            self.is_running = True
            
            # Start main loop
            while self.is_running:
                try:
                    # Check risk limits
                    within_limits, reason = await self.risk.check_limits()
                    if not within_limits:
                        logger.warning(f"Risk limit exceeded: {reason}")
                        continue
                        
                    # Execute pending trades
                    await self.strategy.execute_pending()
                    
                    # Update analytics
                    await self.analytics.update()
                    
                    # Small delay to prevent excessive CPU usage
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}")
                    await asyncio.sleep(5)  # Longer delay on error
                    
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"CryptoBot crashed: {str(e)}")
            await self.stop()
            
    async def stop(self):
        """Stop the trading bot."""
        try:
            logger.info("Stopping CryptoBot...")
            self.is_running = False
            
            # Stop all components
            await self.strategy.stop()
            await self.risk.stop()
            await self.analytics.stop()
            
            # Close API clients
            await self.birdeye.close()
            await self.jupiter.close()
            
            logger.info("CryptoBot stopped successfully")
            
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error stopping CryptoBot: {str(e)}")
            
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status.
        
        Returns:
            Dict with status information
        """
        return {
            'is_running': self.is_running,
            'last_error': self.last_error,
            'wallet_connected': self.wallet.is_connected() if self.wallet else False,
            'performance': self.analytics.get_summary() if self.analytics else {},
            'positions': self.strategy.get_positions() if self.strategy else []
        }
