"""
Backtesting module for CryptoBot
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
import numpy as np
from analysis import TechnicalAnalyzer, PriceData, AnalysisResult
from trading_engine import TradeResult
from risk_manager import RiskConfig

logger = logging.getLogger('CryptoBot.Backtesting')

@dataclass
class Trade:
    token: str
    entry_price: float
    exit_price: Optional[float]
    size: float
    side: str  # 'long' or 'short'
    entry_time: datetime
    exit_time: Optional[datetime]
    pnl: Optional[float]
    fees: float
    reason: str

@dataclass
class BacktestResult:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    trades: List[Trade]
    equity_curve: pd.Series
    metrics: Dict[str, float]

class BacktestEngine:
    def __init__(self, 
                 technical_analyzer: TechnicalAnalyzer,
                 risk_config: RiskConfig,
                 initial_capital: float = 100.0,
                 fee_rate: float = 0.0005):  # 0.05% fee
        self.analyzer = technical_analyzer
        self.risk_config = risk_config
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.current_capital = initial_capital
        self.current_positions: Dict[str, Trade] = {}
        
    def _calculate_position_size(self, price: float, volatility: float) -> float:
        """Calculate position size based on volatility and risk parameters"""
        try:
            # Kelly Criterion with safety factor
            win_rate = len([t for t in self.trades if t.pnl and t.pnl > 0]) / max(len(self.trades), 1)
            avg_win = np.mean([t.pnl for t in self.trades if t.pnl and t.pnl > 0]) if self.trades else 0
            avg_loss = abs(np.mean([t.pnl for t in self.trades if t.pnl and t.pnl < 0])) if self.trades else 0
            
            if avg_loss == 0:
                kelly = 0.1  # Default to 10% when no loss data
            else:
                kelly = (win_rate * avg_win/avg_loss - (1-win_rate)) / (avg_win/avg_loss)
                
            # Apply safety factor and volatility adjustment
            safety_factor = 0.5
            vol_adjustment = 1.0 / (1.0 + volatility)
            position_size = self.current_capital * kelly * safety_factor * vol_adjustment
            
            # Apply risk limits
            max_position = self.current_capital * self.risk_config.max_position_size
            position_size = min(position_size, max_position)
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return self.current_capital * 0.1
            
    def _calculate_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics"""
        try:
            if not self.trades:
                return {}
                
            # Basic metrics
            pnls = [t.pnl for t in self.trades if t.pnl is not None]
            if not pnls:
                return {}
                
            total_pnl = sum(pnls)
            winning_trades = len([p for p in pnls if p > 0])
            
            # Calculate returns
            returns = pd.Series(self.equity_curve).pct_change().dropna()
            if len(returns) < 2:
                return {}
                
            # Risk-free rate (assume 2% annual)
            rf_rate = 0.02 / 365
            
            # Sharpe Ratio
            excess_returns = returns - rf_rate
            sharpe = np.sqrt(365) * excess_returns.mean() / returns.std() if returns.std() != 0 else 0
            
            # Sortino Ratio
            downside_returns = returns[returns < 0]
            sortino = np.sqrt(365) * excess_returns.mean() / downside_returns.std() if len(downside_returns) > 0 else 0
            
            # Maximum Drawdown
            cumulative_returns = (1 + returns).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = drawdowns.min()
            
            return {
                'total_pnl': total_pnl,
                'win_rate': winning_trades / len(pnls),
                'avg_win': np.mean([p for p in pnls if p > 0]) if winning_trades > 0 else 0,
                'avg_loss': np.mean([p for p in pnls if p < 0]) if len(pnls) - winning_trades > 0 else 0,
                'profit_factor': abs(np.sum([p for p in pnls if p > 0]) / np.sum([p for p in pnls if p < 0]))
                if np.sum([p for p in pnls if p < 0]) != 0 else float('inf'),
                'sharpe_ratio': sharpe,
                'sortino_ratio': sortino,
                'max_drawdown': max_drawdown,
                'avg_trade_duration': np.mean([
                    (t.exit_time - t.entry_time).total_seconds()/3600 
                    for t in self.trades if t.exit_time
                ])
            }
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            return {}
            
    async def _check_exit_signals(self, token: str, analysis: AnalysisResult) -> Optional[str]:
        """Check for exit signals"""
        try:
            position = self.current_positions.get(token)
            if not position:
                return None
                
            # Exit signals based on technical analysis
            if position.side == 'long':
                # Exit long positions
                if analysis.rsi > 70 and analysis.macd < analysis.macd_signal:
                    return "overbought_macd_cross"
                if analysis.price < analysis.support:
                    return "support_breach"
                if analysis.trend in ['strong_downtrend', 'weak_downtrend']:
                    return "trend_reversal"
                    
            else:  # short position
                # Exit short positions
                if analysis.rsi < 30 and analysis.macd > analysis.macd_signal:
                    return "oversold_macd_cross"
                if analysis.price > analysis.resistance:
                    return "resistance_breach"
                if analysis.trend in ['strong_uptrend', 'weak_uptrend']:
                    return "trend_reversal"
                    
            return None
            
        except Exception as e:
            logger.error(f"Error checking exit signals: {str(e)}")
            return None
            
    async def _check_entry_signals(self, token: str, analysis: AnalysisResult) -> Optional[str]:
        """Check for entry signals"""
        try:
            # Don't enter if we already have a position
            if token in self.current_positions:
                return None
                
            # Entry signals based on technical analysis
            if (analysis.rsi < 30 and 
                analysis.macd > analysis.macd_signal and 
                analysis.price > analysis.support and
                analysis.trend in ['weak_uptrend', 'strong_uptrend']):
                return "long"
                
            if (analysis.rsi > 70 and 
                analysis.macd < analysis.macd_signal and 
                analysis.price < analysis.resistance and
                analysis.trend in ['weak_downtrend', 'strong_downtrend']):
                return "short"
                
            return None
            
        except Exception as e:
            logger.error(f"Error checking entry signals: {str(e)}")
            return None
            
    async def run_backtest(self, token: str, start_date: datetime, end_date: datetime) -> BacktestResult:
        """Run backtest simulation"""
        try:
            logger.info(f"Starting backtest for {token} from {start_date} to {end_date}")
            
            # Get historical data
            price_data = await self.analyzer.get_historical_prices(
                token,
                (end_date - start_date).days
            )
            
            if not price_data:
                raise ValueError("No price data available")
                
            # Reset state
            self.trades = []
            self.equity_curve = [self.initial_capital]
            self.current_capital = self.initial_capital
            self.current_positions = {}
            
            # Run simulation
            for i in range(len(price_data)):
                current_time = price_data[i].timestamp
                if current_time < start_date or current_time > end_date:
                    continue
                    
                # Get analysis for current window
                window_data = price_data[max(0, i-100):i+1]
                analysis = await self.analyzer.analyze_token(token)
                if not analysis:
                    continue
                    
                # Check exit signals first
                exit_reason = await self._check_exit_signals(token, analysis)
                if exit_reason:
                    position = self.current_positions[token]
                    exit_price = price_data[i].close
                    pnl = (exit_price - position.entry_price) * position.size
                    if position.side == 'short':
                        pnl = -pnl
                        
                    # Apply fees
                    fees = exit_price * position.size * self.fee_rate
                    pnl -= fees
                    
                    # Update position and capital
                    self.current_capital += pnl
                    position.exit_price = exit_price
                    position.exit_time = current_time
                    position.pnl = pnl
                    position.fees += fees
                    position.reason += f", exit: {exit_reason}"
                    
                    # Record trade
                    self.trades.append(position)
                    del self.current_positions[token]
                    
                # Check entry signals
                else:
                    entry_signal = await self._check_entry_signals(token, analysis)
                    if entry_signal:
                        # Calculate position size
                        size = self._calculate_position_size(
                            analysis.price,
                            analysis.volatility
                        )
                        
                        # Apply fees
                        fees = analysis.price * size * self.fee_rate
                        self.current_capital -= fees
                        
                        # Record new position
                        self.current_positions[token] = Trade(
                            token=token,
                            entry_price=analysis.price,
                            exit_price=None,
                            size=size,
                            side=entry_signal,
                            entry_time=current_time,
                            exit_time=None,
                            pnl=None,
                            fees=fees,
                            reason=f"entry: {entry_signal}"
                        )
                        
                # Record equity
                self.equity_curve.append(self.current_capital)
                
            # Close any open positions at the end
            for token, position in list(self.current_positions.items()):
                exit_price = price_data[-1].close
                pnl = (exit_price - position.entry_price) * position.size
                if position.side == 'short':
                    pnl = -pnl
                    
                fees = exit_price * position.size * self.fee_rate
                pnl -= fees
                
                self.current_capital += pnl
                position.exit_price = exit_price
                position.exit_time = end_date
                position.pnl = pnl
                position.fees += fees
                position.reason += ", exit: backtest_end"
                
                self.trades.append(position)
                del self.current_positions[token]
                
            # Calculate final metrics
            metrics = self._calculate_metrics()
            
            return BacktestResult(
                total_trades=len(self.trades),
                winning_trades=len([t for t in self.trades if t.pnl and t.pnl > 0]),
                losing_trades=len([t for t in self.trades if t.pnl and t.pnl < 0]),
                win_rate=metrics.get('win_rate', 0),
                total_pnl=metrics.get('total_pnl', 0),
                max_drawdown=metrics.get('max_drawdown', 0),
                sharpe_ratio=metrics.get('sharpe_ratio', 0),
                sortino_ratio=metrics.get('sortino_ratio', 0),
                trades=self.trades,
                equity_curve=pd.Series(self.equity_curve),
                metrics=metrics
            )
            
        except Exception as e:
            logger.error(f"Error running backtest: {str(e)}")
            raise
