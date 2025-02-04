"""Risk management system for the trading bot"""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RiskConfig:
    max_position_size: float = 0.5  # Maximum position size in SOL
    max_daily_loss: float = 1.0     # Maximum daily loss in SOL
    max_trade_count: int = 10       # Maximum number of trades per day
    min_liquidity_usd: float = 50000  # Minimum liquidity in USD
    max_slippage: float = 0.10      # Maximum allowed slippage (10%)
    emergency_stop_loss: float = 0.20  # Emergency stop loss (20%)
    profit_lock_threshold: float = 0.50  # Lock in profits at 50% gain
    trailing_stop_distance: float = 0.10  # Trailing stop distance (10%)

class RiskManager:
    def __init__(self, config: Optional[Dict] = None):
        """Initialize RiskManager with configuration"""
        config = config or {}
        self.config = RiskConfig(
            max_position_size=config.get('max_position_size_sol', 0.5),
            max_daily_loss=config.get('max_daily_loss_sol', 1.0),
            max_trade_count=config.get('max_trades_per_day', 10),
            min_liquidity_usd=config.get('min_liquidity_usd', 50000),
            max_slippage=config.get('max_slippage_percent', 10) / 100,
            emergency_stop_loss=config.get('emergency_stop_loss', 20) / 100,
            profit_lock_threshold=config.get('profit_lock_threshold', 50) / 100,
            trailing_stop_distance=config.get('trailing_stop_percent', 10) / 100
        )
        self.daily_stats = {
            'date': datetime.now().date(),
            'total_loss': 0.0,
            'trade_count': 0,
            'wins': 0,
            'losses': 0
        }
        self.active_positions = {}
        
    def can_open_position(self, token_info: Dict, size: float) -> Dict:
        """Check if opening a position meets risk criteria"""
        try:
            # Reset daily stats if it's a new day
            self._reset_daily_stats_if_needed()
            
            # Check if we've hit daily limits
            if self.daily_stats['total_loss'] <= -self.config.max_daily_loss:
                return {
                    'allowed': False,
                    'reason': f"Daily loss limit reached: {self.daily_stats['total_loss']} SOL"
                }
                
            if self.daily_stats['trade_count'] >= self.config.max_trade_count:
                return {
                    'allowed': False,
                    'reason': f"Daily trade limit reached: {self.daily_stats['trade_count']}"
                }
                
            # Check position size
            if size > self.config.max_position_size:
                return {
                    'allowed': False,
                    'reason': f"Position size {size} SOL exceeds maximum {self.config.max_position_size} SOL"
                }
                
            # Check liquidity
            if token_info.get('liquidity_usd', 0) < self.config.min_liquidity_usd:
                return {
                    'allowed': False,
                    'reason': f"Insufficient liquidity: ${token_info.get('liquidity_usd', 0)}"
                }
                
            # All checks passed
            return {'allowed': True}
            
        except Exception as e:
            logger.error(f"Error in risk check: {str(e)}")
            return {'allowed': False, 'reason': str(e)}
            
    def update_position(self, position_id: str, current_price: float) -> Dict:
        """Update and check position risk levels"""
        try:
            if position_id not in self.active_positions:
                return {'action': 'error', 'reason': 'Position not found'}
                
            position = self.active_positions[position_id]
            entry_price = position['entry_price']
            size = position['size']
            
            # Calculate current P&L
            pnl = (current_price - entry_price) * size
            pnl_percentage = (current_price - entry_price) / entry_price
            
            # Update highest price seen if profitable
            if current_price > position.get('highest_price', entry_price):
                position['highest_price'] = current_price
                
            # Check emergency stop loss
            if pnl_percentage <= -self.config.emergency_stop_loss:
                return {
                    'action': 'close',
                    'reason': f'Emergency stop loss triggered at {pnl_percentage:.2%}'
                }
                
            # Check trailing stop if in profit
            highest_price = position.get('highest_price', entry_price)
            if highest_price > entry_price:
                trailing_stop_price = highest_price * (1 - self.config.trailing_stop_distance)
                if current_price < trailing_stop_price:
                    return {
                        'action': 'close',
                        'reason': f'Trailing stop triggered at {pnl_percentage:.2%} profit'
                    }
                    
            # Check profit lock
            if pnl_percentage >= self.config.profit_lock_threshold:
                return {
                    'action': 'close',
                    'reason': f'Profit target reached at {pnl_percentage:.2%}'
                }
                
            # Position can remain open
            return {'action': 'hold'}
            
        except Exception as e:
            logger.error(f"Error updating position: {str(e)}")
            return {'action': 'error', 'reason': str(e)}
            
    def record_trade_result(self, pnl: float):
        """Record trade result for daily statistics"""
        try:
            self._reset_daily_stats_if_needed()
            
            self.daily_stats['trade_count'] += 1
            if pnl > 0:
                self.daily_stats['wins'] += 1
            else:
                self.daily_stats['losses'] += 1
                self.daily_stats['total_loss'] += min(0, pnl)
                
        except Exception as e:
            logger.error(f"Error recording trade result: {str(e)}")
            
    def _reset_daily_stats_if_needed(self):
        """Reset daily stats if it's a new day"""
        current_date = datetime.now().date()
        if current_date != self.daily_stats['date']:
            self.daily_stats = {
                'date': current_date,
                'total_loss': 0.0,
                'trade_count': 0,
                'wins': 0,
                'losses': 0
            }
            
    def get_position_size(self, token_info: Dict, wallet_balance: float) -> float:
        """Calculate safe position size based on risk parameters"""
        try:
            # Base position size on wallet balance
            max_size = min(
                wallet_balance * 0.1,  # 10% of wallet
                self.config.max_position_size
            )
            
            # Adjust based on liquidity
            liquidity = token_info.get('liquidity_usd', 0)
            if liquidity < self.config.min_liquidity_usd:
                return 0
                
            # Reduce size if liquidity is low
            liquidity_factor = min(1.0, liquidity / (self.config.min_liquidity_usd * 2))
            
            # Consider volatility
            volatility = abs(token_info.get('price_change_24h', 0)) / 100
            volatility_factor = max(0.1, 1 - volatility)
            
            # Calculate final size
            position_size = max_size * liquidity_factor * volatility_factor
            
            return round(position_size, 3)  # Round to 3 decimals
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return 0
            
    def calculate_position_size(self, token_info: Dict, wallet_balance: float) -> float:
        """Calculate optimal position size based on volatility and wallet balance"""
        try:
            # Get volatility from token info
            volatility = token_info.get('volatility_24h', 0.5)  # Default to 50% if not available
            
            # Base position size on wallet balance
            base_size = wallet_balance * 0.1  # Start with 10% of wallet
            
            # Adjust based on volatility
            volatility_factor = 1 - (volatility / 2)  # Reduce size as volatility increases
            position_size = base_size * volatility_factor
            
            # Cap at max position size
            return min(position_size, self.config.max_position_size)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return 0.0
            
    def calculate_stop_loss(self, entry_price: float, token_info: Dict) -> float:
        """Calculate dynamic stop loss based on volatility"""
        try:
            volatility = token_info.get('volatility_24h', 0.5)
            atr = token_info.get('atr_24h', volatility * entry_price)  # Use ATR if available
            
            # Base stop loss on volatility and ATR
            stop_distance = max(
                atr * 1.5,  # 1.5x ATR
                entry_price * volatility * 0.5,  # Half of daily volatility
                entry_price * self.config.emergency_stop_loss  # Minimum stop loss
            )
            
            return entry_price - stop_distance
            
        except Exception as e:
            logger.error(f"Error calculating stop loss: {str(e)}")
            return entry_price * (1 - self.config.emergency_stop_loss)
            
    def calculate_take_profit(self, entry_price: float, stop_loss: float) -> float:
        """Calculate take profit based on risk:reward ratio"""
        try:
            # Calculate risk in price terms
            risk = entry_price - stop_loss
            
            # Use 2:1 reward:risk ratio minimum
            return entry_price + (risk * 2)
            
        except Exception as e:
            logger.error(f"Error calculating take profit: {str(e)}")
            return entry_price * (1 + self.config.profit_lock_threshold)

    def validate_trade(self, price: float, liquidity: float, market_cap: float) -> bool:
        """Validate if a trade meets risk management criteria"""
        # Check if position size is too large relative to liquidity
        position_size = self.calculate_position_size({'liquidity_usd': liquidity}, 1000)
        if position_size < 10:  # Minimum trade size of $10
            return False
            
        # Check if market cap is reasonable (not too small or too large)
        if market_cap < 100000 or market_cap > 1000000000:
            return False
            
        # Check if liquidity is sufficient
        if liquidity < 50000:  # Minimum liquidity of $50k
            return False
            
        return True
