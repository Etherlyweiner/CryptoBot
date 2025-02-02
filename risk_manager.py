import os
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from wallet import PhantomWallet

logger = logging.getLogger('CryptoBot.Risk')

@dataclass
class RiskConfig:
    max_position_size: float = 0.2  # 20% of portfolio
    max_trades_per_day: int = 10
    daily_loss_limit: float = 0.05  # 5% of portfolio
    max_drawdown: float = 0.1  # 10% max drawdown
    min_sol_balance: float = 0.05  # Minimum SOL to keep
    position_scaling: bool = True  # Scale position size based on volatility
    volatility_lookback: int = 14  # Days to look back for volatility calculation
    risk_per_trade: float = 0.01  # 1% risk per trade

@dataclass
class PositionInfo:
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    timestamp: datetime

class RiskManager:
    def __init__(self, wallet: PhantomWallet, config: Optional[RiskConfig] = None):
        self.wallet = wallet
        self.config = config or RiskConfig()
        self._positions: Dict[str, PositionInfo] = {}
        self._daily_trades = 0
        self._daily_pnl = 0.0
        self._last_reset = datetime.utcnow()
        self._initial_portfolio_value = None
        self._peak_portfolio_value = None
        
    async def initialize(self):
        """Initialize risk manager with current portfolio value"""
        try:
            portfolio_value = await self._get_portfolio_value()
            self._initial_portfolio_value = portfolio_value
            self._peak_portfolio_value = portfolio_value
            logger.info(f"Risk manager initialized with portfolio value: {portfolio_value} SOL")
        except Exception as e:
            logger.error(f"Failed to initialize risk manager: {str(e)}")
            raise
            
    async def _get_portfolio_value(self) -> float:
        """Get total portfolio value in SOL"""
        try:
            # Get SOL balance
            sol_balance = await self.wallet.get_balance()
            if sol_balance is None:
                raise ValueError("Failed to get SOL balance")
                
            # Get token balances and convert to SOL value
            total_value = sol_balance
            token_accounts = await self.wallet.get_token_accounts()
            
            # TODO: Implement token price fetching and conversion to SOL value
            
            return total_value
            
        except Exception as e:
            logger.error(f"Error getting portfolio value: {str(e)}")
            raise
            
    def _reset_daily_metrics(self):
        """Reset daily trading metrics"""
        current_time = datetime.utcnow()
        if current_time - self._last_reset > timedelta(days=1):
            self._daily_trades = 0
            self._daily_pnl = 0.0
            self._last_reset = current_time
            
    async def can_trade(self, token: str, amount: float) -> tuple[bool, str]:
        """Check if a trade is allowed based on risk parameters"""
        try:
            self._reset_daily_metrics()
            
            # Check daily trade limit
            if self._daily_trades >= self.config.max_trades_per_day:
                return False, "Daily trade limit reached"
                
            # Check portfolio value and drawdown
            portfolio_value = await self._get_portfolio_value()
            if self._peak_portfolio_value:
                drawdown = (self._peak_portfolio_value - portfolio_value) / self._peak_portfolio_value
                if drawdown > self.config.max_drawdown:
                    return False, f"Max drawdown exceeded: {drawdown:.2%}"
                    
            # Check daily loss limit
            if self._daily_pnl < -portfolio_value * self.config.daily_loss_limit:
                return False, "Daily loss limit reached"
                
            # Check position size
            max_position = portfolio_value * self.config.max_position_size
            if amount > max_position:
                return False, f"Position size exceeds maximum: {amount} > {max_position}"
                
            # Check minimum SOL balance
            sol_balance = await self.wallet.get_balance()
            if sol_balance is None or sol_balance < self.config.min_sol_balance:
                return False, "Insufficient SOL balance"
                
            return True, "Trade allowed"
            
        except Exception as e:
            logger.error(f"Error checking trade permissions: {str(e)}")
            return False, f"Error: {str(e)}"
            
    async def calculate_position_size(self, token: str, price: float) -> Optional[float]:
        """Calculate appropriate position size based on risk parameters"""
        try:
            portfolio_value = await self._get_portfolio_value()
            
            # Base position size on risk per trade
            position_size = portfolio_value * self.config.risk_per_trade
            
            if self.config.position_scaling:
                # TODO: Implement volatility-based position scaling
                pass
                
            # Ensure position size doesn't exceed limits
            max_position = portfolio_value * self.config.max_position_size
            position_size = min(position_size, max_position)
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return None
            
    async def update_position(self, token: str, trade_result: Dict):
        """Update position information after a trade"""
        try:
            self._daily_trades += 1
            
            current_position = self._positions.get(token)
            if current_position:
                # Update existing position
                realized_pnl = (trade_result['price'] - current_position.entry_price) * current_position.size
                self._daily_pnl += realized_pnl
            
            # Record new position
            self._positions[token] = PositionInfo(
                size=trade_result['size'],
                entry_price=trade_result['price'],
                current_price=trade_result['price'],
                unrealized_pnl=0.0,
                realized_pnl=self._daily_pnl,
                timestamp=datetime.utcnow()
            )
            
            # Update peak portfolio value
            portfolio_value = await self._get_portfolio_value()
            if portfolio_value > (self._peak_portfolio_value or 0):
                self._peak_portfolio_value = portfolio_value
                
        except Exception as e:
            logger.error(f"Error updating position: {str(e)}")
            
    def get_position(self, token: str) -> Optional[PositionInfo]:
        """Get current position information for a token"""
        return self._positions.get(token)
        
    async def get_portfolio_stats(self) -> Dict:
        """Get current portfolio statistics"""
        try:
            portfolio_value = await self._get_portfolio_value()
            return {
                'portfolio_value': portfolio_value,
                'daily_pnl': self._daily_pnl,
                'daily_trades': self._daily_trades,
                'drawdown': ((self._peak_portfolio_value or portfolio_value) - portfolio_value) / 
                           (self._peak_portfolio_value or portfolio_value) if self._peak_portfolio_value else 0.0,
                'positions': len(self._positions),
                'realized_pnl': sum(pos.realized_pnl for pos in self._positions.values()),
                'unrealized_pnl': sum(pos.unrealized_pnl for pos in self._positions.values())
            }
        except Exception as e:
            logger.error(f"Error getting portfolio stats: {str(e)}")
            return {}
