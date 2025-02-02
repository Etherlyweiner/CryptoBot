"""
Risk monitoring and analysis for CryptoBot with enhanced caching and error handling
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
import asyncio
import logging
from datetime import datetime, timedelta
import ccxt
from config import config
from logging_config import get_logger
from dataclasses import dataclass
from asyncio import Lock
from bot import CryptoBot  # Add this import

logger = get_logger('RiskMonitor')

@dataclass
class RiskMetrics:
    """Data class for risk metrics"""
    symbol: str
    var: float  # Value at Risk
    sharpe: float  # Sharpe Ratio
    max_drawdown: float  # Maximum Drawdown
    drawdown: pd.Series  # Historical drawdown series
    var_change: float  # Change in VaR
    sharpe_change: float  # Change in Sharpe
    drawdown_change: float  # Change in drawdown
    volatility: float  # Current volatility
    beta: float  # Market beta
    timestamp: datetime

class RiskMonitorNew:
    def __init__(self, bot: CryptoBot):
        """Initialize risk monitor"""
        try:
            logger.info("Initializing RiskMonitor...")
            self.bot = bot
            self.exchange = bot.exchange  # Use the bot's exchange instance
            self._risk_metrics_cache: Dict[str, RiskMetrics] = {}
            self._last_update: Dict[str, datetime] = {}
            self._cache_duration = 300  # 5 minutes
            self._cache_lock = Lock()
            self._metrics_calculation_lock = Lock()
            self._historical_data: Dict[str, pd.DataFrame] = {}
            logger.info("RiskMonitor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RiskMonitor: {str(e)}")
            raise

    def get_risk_metrics(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get risk metrics for a symbol"""
        try:
            logger.info(f"Calculating risk metrics for {symbol}")
            
            # Get historical data
            data = self.bot.get_ohlcv_data(symbol, timeframe='1h', limit=100)
            if data is None or data.empty:
                logger.error(f"No data available for risk analysis for {symbol}")
                return None
            
            # Calculate returns
            df = data.copy()
            df['returns'] = df['close'].pct_change()
            
            # Drop NaN values
            df = df.dropna()
            
            if df.empty:
                logger.error(f"No valid return data for risk analysis for {symbol}")
                return None
            
            # Calculate risk metrics
            returns = df['returns'].values
            
            # Value at Risk (VaR)
            var = float(np.percentile(returns, 5))
            var_change = float(np.mean(returns) / np.std(returns)) if len(returns) > 1 else 0
            
            # Sharpe Ratio (assuming 0% risk-free rate for simplicity)
            returns_mean = float(np.mean(returns))
            returns_std = float(np.std(returns))
            sharpe = float(np.sqrt(252) * (returns_mean / returns_std)) if returns_std > 0 else 0
            
            # Calculate rolling mean for sharpe change
            rolling_returns = pd.Series(returns).rolling(window=20)
            rolling_means = rolling_returns.mean()
            rolling_stds = rolling_returns.std()
            rolling_sharpes = np.sqrt(252) * (rolling_means / rolling_stds)
            sharpe_change = float(rolling_sharpes.diff().iloc[-1]) if not rolling_sharpes.empty else 0
            
            # Maximum Drawdown
            cumulative_returns = (1 + pd.Series(returns)).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = float(drawdowns.min() * 100)  # Convert to percentage
            drawdown_change = float(drawdowns.diff().iloc[-1] * 100) if not drawdowns.empty else 0
            
            # Create result dictionary with proper error handling
            result = {
                'var': abs(var * 100),  # Convert to percentage
                'var_change': var_change * 100,
                'sharpe': max(min(sharpe, 10), -10),  # Clip extreme values
                'sharpe_change': max(min(sharpe_change * 100, 100), -100),  # Clip and convert to percentage
                'max_drawdown': abs(max_drawdown),
                'drawdown_change': max(min(drawdown_change, 100), -100),  # Clip extreme values
                'drawdown': pd.Series(drawdowns * 100, index=df.index)  # Historical drawdown for plotting
            }
            
            logger.info(f"Successfully calculated risk metrics for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics for {symbol}: {str(e)}", exc_info=True)
            return None

    def _calculate_risk_metrics(self, symbol: str) -> Optional[RiskMetrics]:
        """Calculate risk metrics for a symbol"""
        try:
            # Get historical data
            df = self._get_historical_data(symbol)
            if df is None or df.empty:
                return None

            # Calculate returns
            df['returns'] = df['close'].pct_change()
            df = df.dropna()

            # Calculate Value at Risk (VaR)
            returns = df['returns'].values
            var = np.percentile(returns, 5)  # 95% VaR
            var_prev = np.percentile(returns[:-1], 5)
            var_change = ((var - var_prev) / abs(var_prev)) * 100 if var_prev != 0 else 0

            # Calculate Sharpe Ratio
            risk_free_rate = 0.02  # 2% annual risk-free rate
            excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free rate
            sharpe = np.sqrt(252) * (excess_returns.mean() / excess_returns.std())
            
            # Calculate previous Sharpe for change
            excess_returns_prev = returns[:-1] - (risk_free_rate / 252)
            sharpe_prev = np.sqrt(252) * (excess_returns_prev.mean() / excess_returns_prev.std())
            sharpe_change = sharpe - sharpe_prev

            # Calculate Maximum Drawdown
            cumulative_returns = (1 + df['returns']).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = drawdowns.min() * 100
            
            # Calculate previous max drawdown for change
            drawdowns_prev = drawdowns[:-1]
            max_drawdown_prev = drawdowns_prev.min() * 100
            drawdown_change = max_drawdown - max_drawdown_prev

            # Calculate current volatility
            volatility = returns.std() * np.sqrt(252) * 100

            # Calculate market beta
            market_returns = self._get_market_returns()  # Implement this method
            if market_returns is not None:
                covariance = np.cov(returns, market_returns)[0][1]
                market_variance = np.var(market_returns)
                beta = covariance / market_variance if market_variance != 0 else 1
            else:
                beta = 1

            return RiskMetrics(
                symbol=symbol,
                var=var * 100,  # Convert to percentage
                sharpe=sharpe,
                max_drawdown=max_drawdown,
                drawdown=drawdowns,
                var_change=var_change,
                sharpe_change=sharpe_change,
                drawdown_change=drawdown_change,
                volatility=volatility,
                beta=beta,
                timestamp=datetime.now()
            )

        except Exception as e:
            logger.error(f"Error calculating risk metrics for {symbol}: {str(e)}")
            return None

    def _get_historical_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get historical price data for risk calculations"""
        try:
            # Fetch OHLCV data with proper timeframe
            df = self.bot.fetch_ohlcv(symbol, timeframe='1h', limit=200)
            if df is None or len(df) < 200:
                logger.error(f"Insufficient OHLCV data for {symbol}")
                return None
            df = pd.DataFrame(df, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return None

    def _get_market_returns(self) -> Optional[np.ndarray]:
        """Get market returns for beta calculation"""
        try:
            # This should be implemented to fetch market returns
            # For now, return None to indicate not implemented
            return None
        except Exception as e:
            logger.error(f"Error getting market returns: {str(e)}")
            return None

    async def get_portfolio_risk(self) -> Optional[Dict[str, Any]]:
        """Calculate portfolio-wide risk metrics"""
        try:
            # Get account balance and positions
            balance = await asyncio.get_event_loop().run_in_executor(
                None,
                self.exchange.fetch_balance
            )
            
            if not balance or 'total' not in balance:
                logger.error("Failed to fetch account balance")
                return None
            
            # Calculate total portfolio value in USDT
            total_value = 0.0
            asset_values = {}
            
            for symbol in config.TRADING_PAIRS:
                base = symbol.split('/')[0]
                if base in balance['total']:
                    amount = float(balance['total'][base])
                    if amount > 0:
                        # Get current price
                        metrics = self.get_risk_metrics(symbol)
                        if metrics:
                            value = amount * metrics.current_price
                            asset_values[base] = value
                            total_value += value
            
            # Calculate portfolio metrics
            if total_value > 0:
                # Get correlation matrix of assets
                returns_data = {}
                for symbol in config.TRADING_PAIRS:
                    df = await self.bot.fetch_ohlcv(symbol, timeframe='1h', limit=100)
                    if df is not None:
                        returns_data[symbol] = df['close'].pct_change()
                
                if returns_data:
                    returns_df = pd.DataFrame(returns_data)
                    correlation_matrix = returns_df.corr()
                    
                    # Calculate portfolio volatility using correlation matrix
                    weights = np.array([asset_values.get(s.split('/')[0], 0) / total_value for s in config.TRADING_PAIRS])
                    portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(correlation_matrix * returns_df.std().values[:, None] * returns_df.std().values, weights)))
                else:
                    portfolio_volatility = 0.0
                
                return {
                    'total_value': total_value,
                    'asset_values': asset_values,
                    'portfolio_volatility': portfolio_volatility,
                    'timestamp': datetime.now()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to calculate portfolio risk: {str(e)}")
            return None

    async def close(self):
        """Cleanup resources"""
        try:
            self._risk_metrics_cache.clear()
            self._last_update.clear()
            self._historical_data.clear()
            logger.info("RiskMonitor resources cleaned up")
        except Exception as e:
            logger.error(f"Error during RiskMonitor cleanup: {str(e)}")

class RiskMonitor:
    def __init__(self, bot):
        """Initialize Risk Monitor"""
        try:
            self.bot = bot
            self.risk_metrics = {}
            self.position_limits = {}
            self.alerts = []
            logger.info("RiskMonitor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RiskMonitor: {str(e)}", exc_info=True)
            raise

    def get_risk_metrics(self, symbol: str) -> dict:
        """Get risk metrics for a symbol"""
        try:
            # Get technical indicators
            df = self.bot.get_technical_indicators(symbol)
            if df is None or df.empty:
                logger.error("No data available for risk analysis")
                return None
            
            # Calculate volatility
            returns = df['close'].pct_change()
            volatility = returns.std() * np.sqrt(252)  # Annualized volatility
            
            # Calculate drawdown
            rolling_max = df['close'].expanding().max()
            drawdown = (df['close'] - rolling_max) / rolling_max * 100
            max_drawdown = abs(drawdown.min())
            
            # Calculate Sharpe ratio (assuming risk-free rate of 2%)
            risk_free_rate = 0.02
            excess_returns = returns - risk_free_rate/252
            sharpe_ratio = np.sqrt(252) * excess_returns.mean() / excess_returns.std()
            
            # Calculate Value at Risk (VaR)
            var_95 = np.percentile(returns, 5)
            
            # Get trade metrics
            trade_metrics = self.bot.get_risk_metrics(symbol)
            
            # Combine all metrics
            metrics = {
                'volatility': volatility,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'value_at_risk_95': var_95,
                'current_drawdown': drawdown.iloc[-1],
                'win_rate': trade_metrics['win_rate'] if trade_metrics else 0,
                'profit_factor': trade_metrics['profit_factor'] if trade_metrics else 0
            }
            
            # Update risk metrics cache
            self.risk_metrics[symbol] = {
                'timestamp': datetime.now(),
                'metrics': metrics
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {str(e)}", exc_info=True)
            return None

    def check_risk_limits(self, symbol: str) -> dict:
        """Check if current positions exceed risk limits"""
        try:
            metrics = self.get_risk_metrics(symbol)
            if not metrics:
                return None
            
            alerts = []
            
            # Check volatility
            if metrics['volatility'] > 0.5:  # 50% annualized volatility
                alerts.append({
                    'type': 'warning',
                    'message': f'High volatility detected for {symbol}',
                    'value': metrics['volatility']
                })
            
            # Check drawdown
            if abs(metrics['current_drawdown']) > 10:  # 10% drawdown
                alerts.append({
                    'type': 'warning',
                    'message': f'Significant drawdown for {symbol}',
                    'value': metrics['current_drawdown']
                })
            
            # Check Sharpe ratio
            if metrics['sharpe_ratio'] < 0:
                alerts.append({
                    'type': 'warning',
                    'message': f'Negative Sharpe ratio for {symbol}',
                    'value': metrics['sharpe_ratio']
                })
            
            # Store alerts
            if alerts:
                self.alerts.extend(alerts)
            
            return {
                'status': 'warning' if alerts else 'normal',
                'alerts': alerts,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {str(e)}", exc_info=True)
            return None

    def get_position_exposure(self, symbol: str) -> dict:
        """Calculate current position exposure"""
        try:
            # Get wallet balance
            balance = self.bot.get_wallet_balance()
            if not balance:
                return None
            
            # Get current price
            metrics = self.bot.get_current_metrics(symbol)
            if not metrics:
                return None
            
            current_price = metrics['last_price']
            
            # Calculate exposure
            total_balance = sum(float(val) for val in balance['total'].values())
            position_value = float(balance['total'].get(symbol.split('/')[0], 0)) * current_price
            exposure = position_value / total_balance if total_balance > 0 else 0
            
            return {
                'total_balance': total_balance,
                'position_value': position_value,
                'exposure': exposure,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error calculating position exposure: {str(e)}", exc_info=True)
            return None

    def get_alerts(self, symbol: str = None) -> list:
        """Get active risk alerts"""
        try:
            if symbol:
                return [alert for alert in self.alerts if alert.get('symbol') == symbol]
            return self.alerts
            
        except Exception as e:
            logger.error(f"Error getting alerts: {str(e)}", exc_info=True)
            return []

if __name__ == "__main__":
    async def test_risk_monitor():
        try:
            bot = CryptoBot()
            monitor = RiskMonitorNew(bot)
            
            # Test individual symbol metrics
            btc_metrics = monitor.get_risk_metrics("BTC/USD")
            if btc_metrics:
                print("\nBTC Risk Metrics:")
                for key, value in btc_metrics.items():
                    print(f"{key}: {value}")
            
            # Test portfolio metrics
            portfolio_risk = await monitor.get_portfolio_risk()
            print("\nPortfolio Risk Metrics:")
            for key, value in portfolio_risk.items():
                print(f"{key}: {value}")
                
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
        finally:
            await monitor.close()
            await bot.close()
    
    if __name__ == "__main__":
        asyncio.run(test_risk_monitor())
