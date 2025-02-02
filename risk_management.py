"""
Risk management module for CryptoBot.
Implements position sizing, stop-loss, take-profit, and drawdown protection.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
from decimal import Decimal
import logging
import numpy as np
from collections import defaultdict
import math

logger = logging.getLogger('RiskManagement')

@dataclass
class Position:
    """Represents an open trading position."""
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: Decimal
    quantity: Decimal
    timestamp: pd.Timestamp
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None

@dataclass
class RiskMetrics:
    """Data class for risk metrics."""
    position_exposure: Dict[str, Decimal]  # Symbol -> Exposure in quote currency
    total_exposure: Decimal  # Total exposure in quote currency
    current_drawdown: Decimal  # Current drawdown as percentage
    daily_pnl: Decimal  # Daily profit/loss
    win_rate: Decimal  # Win rate as percentage
    profit_factor: Decimal  # Profit factor (gross profit / gross loss)
    avg_win_loss_ratio: Decimal  # Average win / Average loss
    sharpe_ratio: Optional[Decimal]  # Sharpe ratio if enough data available

class RiskManager:
    """
    Manages trading risk through position sizing, stop losses,
    and portfolio exposure limits.
    """
    
    def __init__(self,
                 initial_capital: Decimal,
                 max_position_size: Decimal = Decimal('0.1'),  # 10% of capital
                 max_total_exposure: Decimal = Decimal('0.5'),  # 50% of capital
                 max_drawdown: Decimal = Decimal('0.15'),  # 15% max drawdown
                 risk_per_trade: Decimal = Decimal('0.02'),  # 2% risk per trade
                 atr_period: int = 14,
                 stop_loss_atr_multiplier: Decimal = Decimal('2.0'),
                 take_profit_atr_multiplier: Decimal = Decimal('3.0'),
                 max_daily_trades: int = 10,  # Maximum trades per day
                 min_win_rate: Decimal = Decimal('0.4'),  # Minimum required win rate
                 correlation_threshold: Decimal = Decimal('0.7'),  # Max correlation between positions
                 min_trade_interval: int = 300,  # 5 minutes
                 max_slippage: Decimal = Decimal('0.001'),  # 0.1%
                 min_volatility: Decimal = Decimal('0.01'),  # 1% minimum volatility
                 max_volatility: Decimal = Decimal('0.05'),  # 5% maximum volatility
                 min_liquidity: Decimal = Decimal('1000000'),  # $1M minimum daily volume
                 use_db: bool = True):
        """Initialize risk manager with conservative parameters."""
        # Validate configuration
        from config_validator import ConfigValidator
        validator = ConfigValidator()
        risk_result = validator.validate_risk_params(
            max_position_size=max_position_size,
            max_total_exposure=max_total_exposure,
            max_drawdown=max_drawdown,
            risk_per_trade=risk_per_trade
        )
        
        trading_result = validator.validate_trading_params(
            min_trade_interval=min_trade_interval,
            max_daily_trades=max_daily_trades,
            min_win_rate=min_win_rate,
            min_profit_factor=Decimal('1.5')
        )
        
        if not risk_result.is_valid or not trading_result.is_valid:
            errors = risk_result.errors + trading_result.errors
            raise ValueError(f"Invalid configuration: {'; '.join(errors)}")
            
        for warning in risk_result.warnings + trading_result.warnings:
            logger.warning(f"Configuration warning: {warning}")
            
        # Initialize standard parameters
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        self.max_position_size = max_position_size
        self.original_max_position_size = max_position_size
        self.max_total_exposure = max_total_exposure
        self.original_max_total_exposure = max_total_exposure
        self.max_drawdown = max_drawdown
        self.risk_per_trade = risk_per_trade
        self.atr_period = atr_period
        self.stop_loss_atr_multiplier = stop_loss_atr_multiplier
        self.take_profit_atr_multiplier = take_profit_atr_multiplier
        self.max_daily_trades = max_daily_trades
        self.min_win_rate = min_win_rate
        self.correlation_threshold = correlation_threshold
        self.min_trade_interval = min_trade_interval
        self.max_slippage = max_slippage
        self.min_volatility = min_volatility
        self.max_volatility = max_volatility
        self.min_liquidity = min_liquidity
        
        # Use more efficient data structures
        self.positions: Dict[str, Position] = {}
        self._daily_trades: List[Dict] = []  # Use underscore for "private" attribute
        self._historical_trades: List[Dict] = []
        self._last_trade_time: Dict[str, pd.Timestamp] = {}
        
        # Database session
        self.use_db = use_db
        if use_db:
            from database import Session
            self.db_session = Session()
            
        # Initialize market analyzer
        from market_analyzer import MarketAnalyzer
        self.market_analyzer = MarketAnalyzer()
            
    def __del__(self):
        """Cleanup database session."""
        if hasattr(self, 'db_session'):
            self.db_session.close()
            
    @property
    def daily_trades(self) -> List[Dict]:
        """Get daily trades with automatic cleanup of old trades."""
        current_time = pd.Timestamp.now()
        cutoff_time = current_time - pd.Timedelta(days=1)
        self._daily_trades = [
            trade for trade in self._daily_trades 
            if trade['time'] > cutoff_time
        ]
        return self._daily_trades
        
    def record_trade(self, trade_data: Dict) -> None:
        """Record a trade with database persistence."""
        # Add to memory
        self._daily_trades.append(trade_data)
        self._historical_trades.append(trade_data)
        self._last_trade_time[trade_data['symbol']] = trade_data['time']
        
        # Persist to database if enabled
        if self.use_db:
            from database import Trade
            db_trade = Trade(
                symbol=trade_data['symbol'],
                side=trade_data['side'],
                entry_price=float(trade_data['entry_price']),
                quantity=float(trade_data['size']),
                timestamp=trade_data['time'],
                stop_loss=float(trade_data['stop_loss']) if 'stop_loss' in trade_data else None,
                take_profit=float(trade_data['take_profit']) if 'take_profit' in trade_data else None
            )
            self.db_session.add(db_trade)
            self.db_session.commit()
            
    def update_capital(self, new_capital: Decimal) -> None:
        """Update capital with metrics persistence."""
        self.current_capital = new_capital
        if new_capital > self.peak_capital:
            self.peak_capital = new_capital
            
        # Record risk metrics if using database
        if self.use_db:
            from database import RiskMetricsHistory
            metrics = RiskMetricsHistory(
                timestamp=pd.Timestamp.now(),
                total_exposure=float(self.get_total_exposure()),
                current_drawdown=float(self.get_drawdown()),
                daily_pnl=float(new_capital - self.initial_capital),
                win_rate=float(self.calculate_win_rate()),
                profit_factor=float(self.calculate_profit_factor()),
                sharpe_ratio=float(self.calculate_sharpe_ratio()) if len(self._historical_trades) > 30 else None
            )
            self.db_session.add(metrics)
            self.db_session.commit()
            
    def update_price_history(self, symbol: str, price: Decimal) -> None:
        """Update price history for correlation calculation."""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        self.price_history[symbol].append(price)
        # Keep last 100 prices for correlation
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol].pop(0)
            
    def calculate_correlation(self, symbol1: str, symbol2: str) -> Optional[Decimal]:
        """Calculate price correlation between two symbols."""
        if (symbol1 not in self.price_history or 
            symbol2 not in self.price_history or
            len(self.price_history[symbol1]) < 30 or
            len(self.price_history[symbol2]) < 30):
            return None
            
        # Use last 30 prices for correlation
        prices1 = self.price_history[symbol1][-30:]
        prices2 = self.price_history[symbol2][-30:]
        
        # Convert to numpy arrays for correlation calculation
        arr1 = np.array([float(p) for p in prices1])
        arr2 = np.array([float(p) for p in prices2])
        
        correlation = np.corrcoef(arr1, arr2)[0, 1]
        return Decimal(str(correlation))
        
    def check_correlation_limits(self, symbol: str, price: Decimal) -> bool:
        """Check if new position would exceed correlation limits."""
        self.update_price_history(symbol, price)
        
        for pos_symbol in self.positions:
            correlation = self.calculate_correlation(symbol, pos_symbol)
            if correlation is not None and abs(correlation) > self.correlation_threshold:
                logger.warning(
                    f"Correlation between {symbol} and {pos_symbol} "
                    f"({float(correlation):.2f}) exceeds threshold "
                    f"({float(self.correlation_threshold):.2f})"
                )
                return False
        return True
        
    def check_daily_trade_limit(self) -> bool:
        """Check if we've exceeded daily trade limit."""
        # Remove trades older than 24 hours
        current_time = pd.Timestamp.now()
        self._daily_trades = [
            trade for trade in self._daily_trades
            if (current_time - trade['time']).total_seconds() < 86400
        ]
        
        if len(self._daily_trades) >= self.max_daily_trades:
            logger.warning(f"Daily trade limit reached: {len(self._daily_trades)} >= {self.max_daily_trades}")
            return False
            
        return True
        
    def calculate_win_rate(self) -> Decimal:
        """Calculate current win rate."""
        if not self._historical_trades:
            return Decimal('1')  # Start optimistic
            
        # Only consider closed trades
        closed_trades = [
            trade for trade in self._historical_trades
            if 'exit_price' in trade
        ]
        
        if not closed_trades:
            return Decimal('1')
            
        winning_trades = sum(1 for trade in closed_trades
            if (
                (trade['side'] == 'buy' and trade['exit_price'] > trade['price']) or
                (trade['side'] == 'sell' and trade['exit_price'] < trade['price'])
            )
        )
        
        return Decimal(str(winning_trades)) / Decimal(str(len(closed_trades)))
        
    def calculate_profit_factor(self) -> Optional[Decimal]:
        """Calculate profit factor (gross profit / gross loss)."""
        gross_profit = sum(trade['pnl'] for trade in self._historical_trades 
                         if trade['pnl'] > 0)
        gross_loss = sum(abs(trade['pnl']) for trade in self._historical_trades 
                        if trade['pnl'] < 0)
        
        if gross_loss == 0:
            return None
            
        return Decimal(str(gross_profit / gross_loss))
        
    def calculate_avg_win_loss_ratio(self) -> Optional[Decimal]:
        """Calculate average win/loss ratio."""
        wins = [trade['pnl'] for trade in self._historical_trades 
               if trade['pnl'] > 0]
        losses = [abs(trade['pnl']) for trade in self._historical_trades 
                 if trade['pnl'] < 0]
        
        if not wins or not losses:
            return None
            
        avg_win = sum(wins) / len(wins)
        avg_loss = sum(losses) / len(losses)
        
        if avg_loss == 0:
            return None
            
        return Decimal(str(avg_win / avg_loss))
        
    def calculate_sharpe_ratio(self) -> Optional[Decimal]:
        """Calculate Sharpe ratio using daily returns."""
        if len(self._historical_trades) < 30:  # Need enough data
            return None
            
        # Calculate daily returns
        daily_pnl = defaultdict(Decimal)
        for trade in self._historical_trades:
            date = trade['exit_time'].date()
            daily_pnl[date] += trade['pnl']
            
        if not daily_pnl:
            return None
            
        # Convert to numpy array for calculations
        returns = np.array([float(pnl) for pnl in daily_pnl.values()])
        
        # Calculate annualized Sharpe ratio
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return None
            
        sharpe = np.sqrt(252) * (avg_return / std_return)  # Annualized
        return Decimal(str(sharpe))
        
    def get_risk_metrics(self) -> RiskMetrics:
        """Get current risk metrics."""
        position_exposure = {
            symbol: pos.quantity * pos.entry_price
            for symbol, pos in self.positions.items()
        }
        
        total_exposure = sum(position_exposure.values(), Decimal('0'))
        
        current_drawdown = (
            (self.peak_capital - self.current_capital) / self.peak_capital
            if self.peak_capital > 0
            else Decimal('0')
        )
        
        # Calculate daily PnL
        current_date = pd.Timestamp.now().date()
        daily_pnl = sum(
            trade['pnl'] for trade in self._daily_trades
            if trade['exit_time'].date() == current_date
        )
        
        return RiskMetrics(
            position_exposure=position_exposure,
            total_exposure=total_exposure,
            current_drawdown=current_drawdown,
            daily_pnl=daily_pnl,
            win_rate=self.calculate_win_rate(),
            profit_factor=self.calculate_profit_factor() or Decimal('0'),
            avg_win_loss_ratio=self.calculate_avg_win_loss_ratio() or Decimal('0'),
            sharpe_ratio=self.calculate_sharpe_ratio()
        )

    def check_exposure_limits(self, symbol: str, new_position_size: Decimal) -> Tuple[bool, str]:
        """Check if adding new position would exceed exposure limits."""
        # Check individual position size limit
        position_size_ratio = new_position_size / self.current_capital
        if position_size_ratio > self.max_position_size:
            msg = (f"Position size {float(position_size_ratio):.1%} exceeds max allowed "
                  f"{float(self.max_position_size):.1%}")
            logger.warning(msg)
            return False, msg
            
        # Calculate total exposure including new position
        current_exposure = sum(
            abs(pos.quantity) * pos.entry_price / self.current_capital
            for pos in self.positions.values()
        )
        new_exposure = current_exposure + position_size_ratio
        
        if new_exposure > self.max_total_exposure:
            msg = (f"Total exposure {float(new_exposure):.1%} would exceed max allowed "
                  f"{float(self.max_total_exposure):.1%}")
            logger.warning(msg)
            return False, msg
            
        return True, ""

    def can_open_position(self, 
                         symbol: str, 
                         price: Decimal, 
                         size: Decimal,
                         market_data: Optional[pd.DataFrame] = None) -> Tuple[bool, str]:
        """Check if a new position can be opened with enhanced market analysis."""
        # First check basic risk parameters
        can_open, reason = self._can_open_position(symbol, price, size)
        if not can_open:
            return False, reason
            
        # Analyze market conditions if data available
        if market_data is not None:
            try:
                market_condition = self.market_analyzer.analyze_market(
                    df=market_data,
                    current_price=price
                )
                
                # Check market risk score
                if market_condition.risk_score > Decimal('0.7'):
                    return False, f"Market risk too high: {float(market_condition.risk_score):.1%}"
                    
                # Adjust position size based on market conditions
                adjusted_size = self._adjust_position_size(
                    size,
                    market_condition
                )
                
                if adjusted_size < size:
                    logger.info(
                        f"Reduced position size from {float(size):.4f} to {float(adjusted_size):.4f} "
                        f"due to market conditions"
                    )
                    size = adjusted_size
                    
            except Exception as e:
                logger.warning(f"Market analysis failed: {str(e)}")
                
        return True, ""
        
    def _can_open_position(self, 
                         symbol: str, 
                         price: Decimal, 
                         size: Decimal) -> Tuple[bool, str]:
        """Check if a new position can be opened."""
        # Validate inputs
        if size <= 0:
            return False, "Position size must be positive"
            
        # Calculate position value
        new_position_value = price * size
        position_size_pct = new_position_value / self.current_capital
        
        # Check individual position size
        if position_size_pct > self.max_position_size:
            msg = (f"Position size ({float(position_size_pct):.1%}) exceeds max allowed "
                  f"{float(self.max_position_size):.1%}")
            logger.warning(msg)
            return False, msg
            
        # Calculate total exposure including new position
        current_exposure = sum(
            abs(pos.quantity) * pos.entry_price / self.current_capital
            for pos in self.positions.values()
        )
        total_exposure = current_exposure + position_size_pct
        
        if total_exposure > self.max_total_exposure:
            msg = (f"Total exposure ({float(total_exposure):.1%}) would exceed max allowed "
                  f"{float(self.max_total_exposure):.1%}")
            logger.warning(msg)
            return False, msg
            
        # Check drawdown
        if not self.check_drawdown():
            return False, "Maximum drawdown exceeded"
            
        # Check daily trade limit
        if not self.check_daily_trade_limit():
            return False, "Daily trade limit reached"
            
        # Check win rate
        win_rate = self.calculate_win_rate()
        if win_rate < self.min_win_rate and len(self._historical_trades) >= 10:
            return False, f"Win rate ({float(win_rate):.1%}) below minimum ({float(self.min_win_rate):.1%})"
            
        # Check volatility
        vol_ok, vol_msg = self.check_volatility(symbol)
        if not vol_ok:
            return False, vol_msg
            
        # Check liquidity
        liq_ok, liq_msg = self.check_liquidity(symbol)
        if not liq_ok:
            return False, liq_msg
            
        # Check trade interval
        interval_ok, interval_msg = self.check_trade_interval(symbol)
        if not interval_ok:
            return False, interval_msg
            
        return True, "Position can be opened"

    def calculate_atr(self,
                     high_prices: pd.Series,
                     low_prices: pd.Series,
                     close_prices: pd.Series) -> Decimal:
        """
        Calculate Average True Range (ATR).
        
        Args:
            high_prices: Series of high prices
            low_prices: Series of low prices
            close_prices: Series of close prices
            
        Returns:
            Current ATR value
        """
        # Calculate True Range
        prev_close = close_prices.shift(1)
        tr1 = high_prices - low_prices
        tr2 = (high_prices - prev_close).abs()
        tr3 = (low_prices - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate ATR
        atr = tr.rolling(window=self.atr_period).mean()
        return Decimal(str(atr.iloc[-1]))

    def calculate_position_size(self,
                              price: Decimal,
                              stop_loss: Decimal,
                              available_capital: Decimal) -> Decimal:
        """
        Calculate position size based on risk per trade.
        
        Args:
            price: Current price
            stop_loss: Stop loss price
            available_capital: Available capital for position
            
        Returns:
            Position size in base currency
        """
        # Calculate maximum loss in quote currency
        max_loss = self.risk_per_trade * available_capital
        
        # Calculate position size based on stop loss distance
        stop_loss_distance = abs(price - stop_loss)
        if stop_loss_distance == 0:
            return Decimal('0')
            
        size = max_loss / stop_loss_distance
        
        # Limit size by max position size
        max_size = (available_capital * self.max_position_size) / price
        size = min(size, max_size)
        
        return size

    def calculate_stop_loss(self,
                          price: Decimal,
                          atr: Decimal,
                          side: str) -> Decimal:
        """
        Calculate stop loss price based on ATR.
        
        Args:
            price: Current price
            atr: Current ATR value
            side: Position side ('long' or 'short')
            
        Returns:
            Stop loss price
        """
        stop_distance = atr * self.stop_loss_atr_multiplier
        if side == 'long':
            return price - stop_distance
        else:  # short
            return price + stop_distance

    def calculate_take_profit(self,
                            price: Decimal,
                            atr: Decimal,
                            side: str) -> Decimal:
        """
        Calculate take profit price based on ATR.
        
        Args:
            price: Current price
            atr: Current ATR value
            side: Position side ('long' or 'short')
            
        Returns:
            Take profit price
        """
        tp_distance = atr * self.take_profit_atr_multiplier
        if side == 'long':
            return price + tp_distance
        else:  # short
            return price - tp_distance

    def close_position(self,
                      symbol: str,
                      price: Decimal,
                      timestamp: pd.Timestamp) -> Optional[Dict]:
        """
        Close an open position and update metrics.
        
        Args:
            symbol: Trading pair symbol
            price: Exit price
            timestamp: Exit timestamp
            
        Returns:
            Trade summary if position was closed, None otherwise
        """
        if symbol not in self.positions:
            return None
            
        position = self.positions[symbol]
        
        # Calculate PnL in quote currency
        if position.side == 'long':
            pnl = (price - position.entry_price) * position.quantity
        else:  # short
            pnl = (position.entry_price - price) * position.quantity
            
        trade_summary = {
            'symbol': symbol,
            'side': position.side,
            'entry_price': position.entry_price,
            'exit_price': price,
            'quantity': position.quantity,
            'pnl': pnl,
            'entry_time': position.timestamp,
            'exit_time': timestamp
        }
        
        # Remove position first
        del self.positions[symbol]
        
        # Update capital and peak capital
        self.current_capital += pnl
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
            
        # Record trade
        self._historical_trades.append(trade_summary)
        self._daily_trades.append(trade_summary)
        
        logger.info(f"Closed position in {symbol}: PnL = {float(pnl)}")
        return trade_summary

    def open_position(self,
                     symbol: str,
                     price: Decimal,
                     size: Decimal,
                     side: str,
                     timestamp: pd.Timestamp,
                     stop_loss: Optional[Decimal] = None,
                     take_profit: Optional[Decimal] = None) -> Optional[Position]:
        """
        Open a new position if risk checks pass.
        
        Args:
            symbol: Trading pair symbol
            price: Entry price
            size: Position size
            side: Position side ('long' or 'short')
            timestamp: Entry timestamp
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            
        Returns:
            Position object if opened, None otherwise
        """
        can_open, reason = self.can_open_position(symbol, price, size)
        if not can_open:
            logger.warning(f"Cannot open position: {reason}")
            return None
            
        position = Position(
            symbol=symbol,
            side=side,
            entry_price=price,
            quantity=size,
            timestamp=timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        self.positions[symbol] = position
        logger.info(f"Opened {side} position in {symbol}: {float(size)} @ {float(price)}")
        
        return position

    def update_position(self,
                       symbol: str,
                       price: Decimal,
                       timestamp: pd.Timestamp) -> Optional[str]:
        """
        Update position and check for stop loss/take profit triggers.
        
        Args:
            symbol: Trading pair symbol
            price: Current price
            timestamp: Current timestamp
            
        Returns:
            Action taken ('closed_sl', 'closed_tp', None)
        """
        if symbol not in self.positions:
            return None
            
        position = self.positions[symbol]
        
        # Check stop loss
        if position.stop_loss is not None:
            if (position.side == 'long' and price <= position.stop_loss) or \
               (position.side == 'short' and price >= position.stop_loss):
                self.close_position(symbol, price, timestamp)
                return 'closed_sl'
                
        # Check take profit
        if position.take_profit is not None:
            if (position.side == 'long' and price >= position.take_profit) or \
               (position.side == 'short' and price <= position.take_profit):
                self.close_position(symbol, price, timestamp)
                return 'closed_tp'
                
        return None

    def check_drawdown(self) -> bool:
        """Check if drawdown exceeds maximum allowed."""
        if self.current_capital >= self.peak_capital:
            self.peak_capital = self.current_capital
            return True
            
        current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        
        logger.debug(f"Current drawdown: {float(current_drawdown):.2%}, Max allowed: {float(self.max_drawdown):.2%}")
        
        # If we've exceeded max drawdown, prevent new positions
        if current_drawdown > self.max_drawdown:
            logger.warning(f"Maximum drawdown exceeded: {float(current_drawdown):.2%} > {float(self.max_drawdown):.2%}")
            return False
            
        return True
        
    def get_drawdown(self) -> Decimal:
        """Get current drawdown as a percentage."""
        if self.current_capital >= self.peak_capital:
            return Decimal('0')
            
        return (self.peak_capital - self.current_capital) / self.peak_capital

    def update_capital(self, new_capital: Decimal):
        """Update current capital and peak capital."""
        self.current_capital = new_capital
        if new_capital > self.peak_capital:
            self.peak_capital = new_capital

    def check_volatility(self, symbol: str) -> Tuple[bool, str]:
        """Check if volatility is within acceptable range."""
        if symbol not in self.volatility_history:
            return True, "No volatility data"
            
        current_volatility = self.calculate_volatility(symbol)
        if current_volatility < self.min_volatility:
            return False, f"Volatility too low: {float(current_volatility):.2%}"
        if current_volatility > self.max_volatility:
            return False, f"Volatility too high: {float(current_volatility):.2%}"
            
        return True, "Volatility within range"
        
    def check_liquidity(self, symbol: str) -> Tuple[bool, str]:
        """Check if liquidity meets minimum requirements."""
        if symbol not in self.liquidity_history:
            return True, "No liquidity data"
            
        current_liquidity = self.calculate_liquidity(symbol)
        if current_liquidity < self.min_liquidity:
            return False, f"Insufficient liquidity: ${float(current_liquidity):,.2f}"
            
        return True, "Sufficient liquidity"
        
    def calculate_volatility(self, symbol: str) -> Decimal:
        """Calculate current volatility using standard deviation of returns."""
        if len(self.volatility_history[symbol]) < 2:
            return Decimal('0')
            
        # Use the volatility history directly instead of calculating
        return self.volatility_history[symbol][-1]
        
    def calculate_liquidity(self, symbol: str) -> Decimal:
        """Calculate current liquidity using rolling average volume."""
        if not self.liquidity_history[symbol]:
            return Decimal('0')
            
        return sum(self.liquidity_history[symbol]) / len(self.liquidity_history[symbol])

    def check_trade_interval(self, symbol: str) -> Tuple[bool, str]:
        """Check if minimum trade interval has passed."""
        if symbol not in self._last_trade_time:
            return True, "No previous trades"
            
        time_diff = (pd.Timestamp.now() - self._last_trade_time[symbol]).total_seconds()
        if time_diff < self.min_trade_interval:
            return False, f"Minimum trade interval not passed: {time_diff} < {self.min_trade_interval}"
            
        return True, "Minimum trade interval passed"

    def _adjust_position_size(self,
                            original_size: Decimal,
                            market_condition: 'MarketCondition') -> Decimal:
        """Adjust position size based on market conditions."""
        # Start with original size
        adjusted_size = original_size
        
        # Reduce size in high volatility conditions
        if market_condition.volatility > self.max_volatility:
            volatility_factor = self.max_volatility / market_condition.volatility
            adjusted_size *= volatility_factor
            
        # Reduce size in ranging markets
        if market_condition.is_ranging:
            adjusted_size *= Decimal('0.7')  # 30% reduction in ranging markets
            
        # Reduce size in low volume conditions
        if market_condition.volume_profile == 'low':
            adjusted_size *= Decimal('0.5')  # 50% reduction in low volume
            
        # Ensure minimum position size
        min_size = self.risk_per_trade * self.current_capital
        adjusted_size = max(adjusted_size, min_size)
        
        return adjusted_size
        
    def update_market_state(self,
                          symbol: str,
                          market_data: pd.DataFrame) -> None:
        """Update market state analysis."""
        try:
            market_condition = self.market_analyzer.analyze_market(
                df=market_data,
                current_price=Decimal(str(market_data['close'].iloc[-1]))
            )
            
            # Record market metrics if using database
            if self.use_db:
                from database import Session
                session = Session()
                # TODO: Add market metrics table and recording
                session.close()
                
            # Update internal state
            self._update_risk_limits(market_condition)
            
        except Exception as e:
            logger.error(f"Failed to update market state: {str(e)}")
            
    def _update_risk_limits(self, market_condition: 'MarketCondition') -> None:
        """Dynamically update risk limits based on market conditions."""
        # Adjust maximum position size based on market risk
        risk_factor = Decimal('1') - market_condition.risk_score
        self.max_position_size = min(
            self.original_max_position_size,
            self.original_max_position_size * risk_factor
        )
        
        # Adjust total exposure limit
        self.max_total_exposure = min(
            self.original_max_total_exposure,
            self.original_max_total_exposure * risk_factor
        )
        
        # Log adjustments
        logger.info(
            f"Updated risk limits based on market conditions: "
            f"max_position_size={float(self.max_position_size):.1%}, "
            f"max_total_exposure={float(self.max_total_exposure):.1%}"
        )
