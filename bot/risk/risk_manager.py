"""Risk management system."""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RiskManager:
    """Manages trading risk and position limits."""
    
    def __init__(self, bot):
        """Initialize risk manager.
        
        Args:
            bot: CryptoBot instance
        """
        self.bot = bot
        self.config = bot.config.get('risk', {})
        
        # Risk limits
        self.max_position_size = self.config.get('max_position_size_sol', 1.0)
        self.max_daily_trades = self.config.get('max_daily_trades', 20)
        self.max_daily_loss = self.config.get('max_daily_loss_percent', 5.0)
        
        # State tracking
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.last_reset = datetime.now()
        
    async def initialize(self):
        """Initialize the risk manager."""
        logger.info("Initialized risk manager")
        
    async def stop(self):
        """Stop the risk manager."""
        logger.info("Stopped risk manager")
        
    def _reset_daily_metrics(self):
        """Reset daily tracking metrics."""
        if (datetime.now() - self.last_reset) > timedelta(days=1):
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.last_reset = datetime.now()
            
    async def check_limits(self) -> Tuple[bool, Optional[str]]:
        """Check if any risk limits are exceeded.
        
        Returns:
            Tuple of (within_limits, reason)
        """
        try:
            self._reset_daily_metrics()
            
            # Check daily trade limit
            if self.daily_trades >= self.max_daily_trades:
                return False, "Daily trade limit exceeded"
                
            # Check daily loss limit
            if abs(self.daily_pnl) > self.max_daily_loss:
                return False, "Daily loss limit exceeded"
                
            return True, None
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {str(e)}")
            return False, str(e)
