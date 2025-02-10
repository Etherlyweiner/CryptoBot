"""Performance analytics system."""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PerformanceAnalytics:
    """Tracks and analyzes trading performance."""
    
    def __init__(self, bot):
        """Initialize analytics.
        
        Args:
            bot: CryptoBot instance
        """
        self.bot = bot
        
        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.total_profit = 0.0
        self.daily_volume = 0.0
        
        # Trade history
        self.trades: List[Dict[str, Any]] = []
        self.positions: Dict[str, Dict[str, Any]] = {}
        
        # Alerts
        self.alerts: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Initialize analytics."""
        logger.info("Initialized performance analytics")
        
    async def stop(self):
        """Stop analytics."""
        logger.info("Stopped performance analytics")
        
    async def update(self):
        """Update performance metrics."""
        try:
            # Update position values
            for token, position in self.positions.items():
                # Get current price
                price = await self.bot.birdeye.get_token_price(token)
                if price:
                    # Update unrealized PnL
                    entry_price = position['entry_price']
                    size = position['size']
                    position['unrealized_pnl'] = (price - entry_price) * size
                    
            # Clean old alerts
            self._clean_old_alerts()
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {str(e)}")
            
    def add_trade(self, trade: Dict[str, Any]):
        """Add a completed trade.
        
        Args:
            trade: Trade data dictionary
        """
        self.trades.append(trade)
        self.total_trades += 1
        
        if trade.get('profit', 0) > 0:
            self.winning_trades += 1
            
        self.total_profit += trade.get('profit', 0)
        self.daily_volume += trade.get('volume', 0)
        
    def add_alert(self, alert_type: str, message: str, severity: str = 'info'):
        """Add a new alert.
        
        Args:
            alert_type: Type of alert
            message: Alert message
            severity: Alert severity (info, warning, error)
        """
        self.alerts.append({
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now()
        })
        
    def _clean_old_alerts(self):
        """Remove alerts older than 24 hours."""
        cutoff = datetime.now() - timedelta(hours=24)
        self.alerts = [
            alert for alert in self.alerts
            if alert['timestamp'] > cutoff
        ]
        
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary.
        
        Returns:
            Dict with summary metrics
        """
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate': round(win_rate, 2),
            'total_profit': round(self.total_profit, 4),
            'daily_volume': round(self.daily_volume, 4),
            'open_positions': len(self.positions)
        }
