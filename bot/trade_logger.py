"""Trade history logging module."""

import json
import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)

class TradeLogger:
    """Trade history logger."""
    
    def __init__(self, log_dir: str = "logs"):
        """Initialize trade logger.
        
        Args:
            log_dir: Directory to store trade logs
        """
        self.log_dir = log_dir
        self.trade_log_file = os.path.join(log_dir, "trades.json")
        
        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Load existing trades
        self.trades: List[Dict] = []
        if os.path.exists(self.trade_log_file):
            try:
                with open(self.trade_log_file, "r") as f:
                    self.trades = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load trade history: {str(e)}")
                
    def log_trade(self, trade_data: Dict[str, Union[str, float, int]]) -> bool:
        """Log a trade.
        
        Args:
            trade_data: Trade data to log
            
        Returns:
            bool: True if trade was logged successfully
        """
        try:
            # Add timestamp if not present
            if "timestamp" not in trade_data:
                trade_data["timestamp"] = datetime.now().isoformat()
                
            # Convert Decimal objects to float for JSON serialization
            for key, value in trade_data.items():
                if isinstance(value, Decimal):
                    trade_data[key] = float(value)
                    
            # Add trade to history
            self.trades.append(trade_data)
            
            # Save to file
            with open(self.trade_log_file, "w") as f:
                json.dump(self.trades, f, indent=2)
                
            logger.info(f"Trade logged: {trade_data}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log trade: {str(e)}")
            return False
            
    def get_trades(self, limit: Optional[int] = None) -> List[Dict]:
        """Get trade history.
        
        Args:
            limit: Maximum number of trades to return, newest first
            
        Returns:
            List of trades
        """
        if limit is None:
            return self.trades
        return self.trades[-limit:]
        
    def get_performance_metrics(self) -> Dict[str, Union[float, int]]:
        """Calculate performance metrics.
        
        Returns:
            Dict containing performance metrics
        """
        if not self.trades:
            return {
                "totalProfitLoss": 0.0,
                "winRate": 0.0,
                "tradeCount": 0
            }
            
        # Calculate total profit/loss
        total_pl = sum(trade.get("profitLoss", 0) for trade in self.trades)
        
        # Calculate win rate
        winning_trades = sum(1 for trade in self.trades if trade.get("profitLoss", 0) > 0)
        win_rate = (winning_trades / len(self.trades)) * 100 if self.trades else 0
        
        return {
            "totalProfitLoss": float(total_pl),
            "winRate": round(win_rate, 2),
            "tradeCount": len(self.trades)
        }
        
    def clear_history(self) -> bool:
        """Clear trade history.
        
        Returns:
            bool: True if history was cleared successfully
        """
        try:
            self.trades = []
            with open(self.trade_log_file, "w") as f:
                json.dump(self.trades, f)
            return True
        except Exception as e:
            logger.error(f"Failed to clear trade history: {str(e)}")
            return False
