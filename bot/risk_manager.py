"""Risk management module."""

import logging
from decimal import Decimal
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class RiskManager:
    """Risk management system."""
    
    def __init__(self, config: Dict):
        """Initialize risk manager.
        
        Args:
            config: Risk management configuration
        """
        self.config = config
        
        # Load risk parameters
        self.max_daily_trades = int(config.get('max_daily_trades', 10))
        self.max_daily_loss = Decimal(str(config.get('max_daily_loss', '1.0')))  # Max 1 SOL loss per day
        self.max_position_size = Decimal(str(config.get('max_position_size', '1.0')))  # Max 1 SOL per trade
        self.max_open_positions = int(config.get('max_open_positions', 3))
        
        # Track daily metrics
        self.daily_trades = 0
        self.daily_pnl = Decimal('0')
        self.open_positions: Dict[str, Dict] = {}  # token -> position data
        
    def can_open_position(self, token: str, size: Decimal, balance: Decimal) -> Tuple[bool, str]:
        """Check if we can open a new position.
        
        Args:
            token: Token address
            size: Position size in SOL
            balance: Current balance in SOL
            
        Returns:
            (can_open, reason)
        """
        try:
            # Check daily trade limit
            if self.daily_trades >= self.max_daily_trades:
                return False, "Daily trade limit reached"
                
            # Check daily loss limit
            if self.daily_pnl <= -self.max_daily_loss:
                return False, "Daily loss limit reached"
                
            # Check position size
            if size > self.max_position_size:
                return False, "Position size too large"
                
            # Check if we already have a position in this token
            if token in self.open_positions:
                return False, "Position already open"
                
            # Check number of open positions
            if len(self.open_positions) >= self.max_open_positions:
                return False, "Too many open positions"
                
            # Check if we have enough balance
            if size > balance * Decimal('0.9'):  # Keep 10% buffer
                return False, "Insufficient balance"
                
            return True, ""
            
        except Exception as e:
            logger.error(f"Error checking position: {str(e)}")
            return False, str(e)
            
    def open_position(self, token: str, entry_price: Decimal, size: Decimal):
        """Record opening a position.
        
        Args:
            token: Token address
            entry_price: Entry price
            size: Position size in SOL
        """
        try:
            self.open_positions[token] = {
                'entry_price': entry_price,
                'size': size,
                'unrealized_pnl': Decimal('0')
            }
            self.daily_trades += 1
            
        except Exception as e:
            logger.error(f"Error opening position: {str(e)}")
            
    def close_position(self, token: str, exit_price: Decimal) -> Optional[Decimal]:
        """Record closing a position.
        
        Args:
            token: Token address
            exit_price: Exit price
            
        Returns:
            Realized PnL if successful
        """
        try:
            position = self.open_positions.get(token)
            if not position:
                return None
                
            # Calculate PnL
            entry_price = position['entry_price']
            size = position['size']
            pnl = (exit_price - entry_price) * size
            
            # Update daily PnL
            self.daily_pnl += pnl
            
            # Remove position
            del self.open_positions[token]
            
            return pnl
            
        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
            return None
            
    def update_position_pnl(self, token: str, current_price: Decimal):
        """Update unrealized PnL for a position.
        
        Args:
            token: Token address
            current_price: Current price
        """
        try:
            position = self.open_positions.get(token)
            if not position:
                return
                
            # Calculate unrealized PnL
            entry_price = position['entry_price']
            size = position['size']
            unrealized_pnl = (current_price - entry_price) * size
            
            # Update position
            position['unrealized_pnl'] = unrealized_pnl
            
        except Exception as e:
            logger.error(f"Error updating position PnL: {str(e)}")
            
    def get_position_risk_metrics(self) -> Dict:
        """Get current risk metrics.
        
        Returns:
            Dict containing risk metrics
        """
        try:
            total_exposure = sum(p['size'] for p in self.open_positions.values())
            total_unrealized_pnl = sum(p['unrealized_pnl'] for p in self.open_positions.values())
            
            return {
                'daily_trades': self.daily_trades,
                'daily_pnl': float(self.daily_pnl),
                'open_positions': len(self.open_positions),
                'total_exposure': float(total_exposure),
                'total_unrealized_pnl': float(total_unrealized_pnl)
            }
            
        except Exception as e:
            logger.error(f"Error getting risk metrics: {str(e)}")
            return {}
