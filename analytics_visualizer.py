"""
Analytics visualization module for CryptoBot
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json
from database import Database
import plotly.express as px
from scipy import stats
import seaborn as sns
import matplotlib.pyplot as plt
from itertools import combinations
import logging
import os

logger = logging.getLogger(__name__)

class AnalyticsVisualizer:
    def __init__(self, database: Database):
        """Initialize visualizer with database connection"""
        self.db = database

    def plot_performance_overview(self, symbol: str, timeframe: str = 'all') -> go.Figure:
        """Create performance overview dashboard"""
        try:
            # Get performance metrics
            metrics = self.db.get_performance_metrics(symbol, timeframe)
            if not metrics:
                return None

            # Get position data
            positions = pd.DataFrame([p for p in self.db.get_position_history(symbol) if isinstance(p, dict)])
            if positions.empty:
                return None
            
            # Convert timestamps
            positions['entry_timestamp'] = pd.to_datetime(positions['entry_timestamp'])
            if 'exit_timestamp' in positions.columns:
                positions['exit_timestamp'] = pd.to_datetime(positions['exit_timestamp'])
            positions.set_index('entry_timestamp', inplace=True)

            # Create figure with subplots
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=(
                    'Cumulative Returns', 'Trade Distribution',
                    'Rolling Returns', 'Monthly Returns',
                    'Position Durations', 'Win/Loss Ratio'
                ),
                specs=[
                    [{"secondary_y": True}, {}],
                    [{"secondary_y": True}, {"type": "heatmap"}],
                    [{}, {}]
                ]
            )

            # 1. Cumulative Returns
            cumulative_pnl = positions['pnl'].cumsum()
            fig.add_trace(
                go.Scatter(x=cumulative_pnl.index, 
                          y=cumulative_pnl.values,
                          name="Cumulative PnL"),
                row=1, col=1
            )

            # Add drawdown on secondary axis
            drawdown = (cumulative_pnl - cumulative_pnl.expanding().max()) / cumulative_pnl.expanding().max()
            fig.add_trace(
                go.Scatter(x=drawdown.index, 
                          y=drawdown.values,
                          name="Drawdown",
                          fill='tozeroy',
                          fillcolor='rgba(255,0,0,0.2)'),
                row=1, col=1,
                secondary_y=True
            )

            # 2. Trade Distribution
            fig.add_trace(
                go.Histogram(x=positions['pnl'],
                            name="Trade PnL Distribution",
                            nbinsx=50),
                row=1, col=2
            )

            # 3. Rolling Returns
            window = 30  # 30-day rolling window
            rolling_returns = positions['pnl'].rolling(window=window).mean()
            fig.add_trace(
                go.Scatter(x=rolling_returns.index,
                          y=rolling_returns.values,
                          name=f"{window}-Day Rolling Returns"),
                row=2, col=1
            )

            # 4. Monthly Returns Heatmap
            monthly_returns = positions['pnl'].resample('ME').sum().to_frame()
            monthly_returns['year'] = monthly_returns.index.year
            monthly_returns['month'] = monthly_returns.index.month
            pivot_table = monthly_returns.pivot(index='year', 
                                              columns='month', 
                                              values='pnl')
            
            if not pivot_table.empty:
                fig.add_trace(
                    go.Heatmap(z=pivot_table.values,
                              x=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                              y=pivot_table.index,
                              colorscale='RdYlGn',
                              name="Monthly Returns"),
                    row=2, col=2
                )

            # 5. Position Durations
            if 'exit_timestamp' in positions.columns:
                durations = (positions['exit_timestamp'] - positions.index).dt.total_seconds() / 3600  # hours
                fig.add_trace(
                    go.Histogram(x=durations,
                                name="Position Duration (hours)",
                                nbinsx=50),
                    row=3, col=1
                )

            # 6. Win/Loss Ratio
            win_loss = {
                'Winning Trades': len(positions[positions['pnl'] > 0]),
                'Losing Trades': len(positions[positions['pnl'] < 0])
            }
            fig.add_trace(
                go.Bar(x=list(win_loss.keys()),
                      y=list(win_loss.values()),
                      name="Win/Loss Distribution"),
                row=3, col=2
            )

            # Update layout
            fig.update_layout(
                height=1200,
                showlegend=True,
                template="plotly_dark",
                title=f"Performance Overview - {symbol} ({timeframe})"
            )

            return fig
        except Exception as e:
            logger.error(f"Error creating performance overview: {str(e)}")
            return None

    def plot_risk_dashboard(self, symbol: str, timeframe: str = 'all') -> go.Figure:
        """Create risk analysis dashboard"""
        try:
            # Get risk metrics
            risk_metrics = self.db.get_risk_analysis(symbol, timeframe)
            if not risk_metrics:
                return None

            # Get position data for additional metrics
            positions = pd.DataFrame([p for p in self.db.get_position_history(symbol) if isinstance(p, dict)])
            if positions.empty:
                return None
            
            # Convert timestamps
            positions['entry_timestamp'] = pd.to_datetime(positions['entry_timestamp'])
            if 'exit_timestamp' in positions.columns:
                positions['exit_timestamp'] = pd.to_datetime(positions['exit_timestamp'])
            positions.set_index('entry_timestamp', inplace=True)

            # Create figure with subplots
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=(
                    'Value at Risk (VaR)', 'Risk-Return Scatter',
                    'Rolling Volatility', 'Beta Analysis',
                    'Drawdown Analysis', 'Risk Metrics Summary'
                ),
                specs=[
                    [{"secondary_y": True}, {}],
                    [{"secondary_y": True}, {}],
                    [{}, {}]
                ]
            )

            # 1. Value at Risk (VaR)
            daily_returns = positions['pnl'].resample('ME').sum()
            sorted_returns = daily_returns.sort_values()
            var_95 = float(np.percentile(daily_returns, 5))
            var_99 = float(np.percentile(daily_returns, 1))
            
            fig.add_trace(
                go.Histogram(x=daily_returns,
                            name="Daily Returns Distribution",
                            nbinsx=50),
                row=1, col=1
            )
            
            # Add VaR lines
            fig.add_vline(x=var_95, line_dash="dash", line_color="red",
                         annotation_text="95% VaR", row=1, col=1)
            fig.add_vline(x=var_99, line_dash="dash", line_color="darkred",
                         annotation_text="99% VaR", row=1, col=1)

            # 2. Risk-Return Scatter
            rolling_returns = positions['pnl'].rolling(window=30).mean()
            rolling_vol = positions['pnl'].rolling(window=30).std()
            
            fig.add_trace(
                go.Scatter(x=rolling_vol,
                          y=rolling_returns,
                          mode='markers',
                          name="Risk-Return Points"),
                row=1, col=2
            )

            # 3. Rolling Volatility
            fig.add_trace(
                go.Scatter(x=rolling_vol.index,
                          y=rolling_vol.values,
                          name="30-Day Rolling Volatility"),
                row=2, col=1
            )

            # 4. Beta Analysis
            if 'beta' in risk_metrics:
                dates = pd.date_range(start=positions.index.min(), 
                                    end=positions.index.max(), 
                                    periods=30)
                fig.add_trace(
                    go.Scatter(x=dates,
                              y=[risk_metrics['beta']] * len(dates),
                              name="Beta"),
                    row=2, col=2
                )

            # 5. Drawdown Analysis
            cumulative = positions['pnl'].cumsum()
            rolling_max = cumulative.expanding().max()
            drawdowns = (cumulative - rolling_max) / rolling_max
            
            fig.add_trace(
                go.Scatter(x=drawdowns.index,
                          y=drawdowns.values,
                          name="Drawdown",
                          fill='tozeroy',
                          fillcolor='rgba(255,0,0,0.2)'),
                row=3, col=1
            )

            # 6. Risk Metrics Summary
            metrics_summary = {
                'VaR (95%)': var_95,
                'VaR (99%)': var_99,
                'Volatility': risk_metrics.get('average_volatility', 0),
                'Beta': risk_metrics.get('beta', 0),
                'Max Drawdown': drawdowns.min()
            }
            
            fig.add_trace(
                go.Bar(x=list(metrics_summary.keys()),
                      y=list(metrics_summary.values()),
                      name="Risk Metrics"),
                row=3, col=2
            )

            # Update layout
            fig.update_layout(
                height=1200,
                showlegend=True,
                template="plotly_dark",
                title=f"Risk Analysis Dashboard - {symbol} ({timeframe})"
            )

            return fig
        except Exception as e:
            logger.error(f"Error creating risk dashboard: {str(e)}")
            return None

    def plot_position_analysis(self, symbol: str) -> go.Figure:
        """Create position analysis dashboard"""
        try:
            # Get position data
            positions = pd.DataFrame([p for p in self.db.get_position_history(symbol) if isinstance(p, dict)])
            if positions.empty:
                return None

            # Convert timestamps
            positions['entry_timestamp'] = pd.to_datetime(positions['entry_timestamp'])
            if 'exit_timestamp' in positions.columns:
                positions['exit_timestamp'] = pd.to_datetime(positions['exit_timestamp'])
            positions.set_index('entry_timestamp', inplace=True)

            # Create figure with subplots
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=(
                    'Position Size Over Time', 'Position Duration Distribution',
                    'Entry/Exit Price Analysis', 'Win Rate by Size',
                    'Time of Day Analysis', 'Position Performance'
                ),
                specs=[
                    [{"secondary_y": True}, {}],
                    [{"secondary_y": True}, {}],
                    [{}, {}]
                ]
            )

            # 1. Position Size Over Time
            fig.add_trace(
                go.Scatter(x=positions.index,
                          y=positions['amount'],
                          mode='markers',
                          name="Position Size"),
                row=1, col=1
            )

            # Add cumulative PnL on secondary axis
            cumulative_pnl = positions['pnl'].cumsum()
            fig.add_trace(
                go.Scatter(x=cumulative_pnl.index,
                          y=cumulative_pnl.values,
                          name="Cumulative PnL",
                          line=dict(color='green')),
                row=1, col=1,
                secondary_y=True
            )

            # 2. Position Duration Distribution
            if 'exit_timestamp' in positions.columns:
                durations = (positions['exit_timestamp'] - positions.index).dt.total_seconds() / 3600  # hours
                fig.add_trace(
                    go.Histogram(x=durations,
                                name="Position Duration (hours)",
                                nbinsx=50),
                    row=1, col=2
                )

            # 3. Entry/Exit Price Analysis
            if all(col in positions.columns for col in ['entry_price', 'exit_price']):
                fig.add_trace(
                    go.Scatter(x=positions.index,
                              y=positions['entry_price'],
                              name="Entry Price",
                              mode='markers'),
                    row=2, col=1
                )
                
                fig.add_trace(
                    go.Scatter(x=positions.index,
                              y=positions['exit_price'],
                              name="Exit Price",
                              mode='markers'),
                    row=2, col=1
                )

            # 4. Win Rate by Size
            size_bins = pd.qcut(positions['amount'], q=5)
            win_rates = positions.groupby(size_bins)['pnl'].apply(lambda x: (x > 0).mean())
            
            fig.add_trace(
                go.Bar(x=[f"Q{i+1}" for i in range(5)],
                      y=win_rates.values,
                      name="Win Rate by Size Quintile"),
                row=2, col=2
            )

            # 5. Time of Day Analysis
            hour_of_day = positions.index.hour
            hourly_pnl = positions.groupby(hour_of_day)['pnl'].mean()
            
            fig.add_trace(
                go.Bar(x=hourly_pnl.index,
                      y=hourly_pnl.values,
                      name="Average PnL by Hour"),
                row=3, col=1
            )

            # 6. Position Performance Metrics
            metrics = {
                'Total Positions': len(positions),
                'Win Rate': (positions['pnl'] > 0).mean(),
                'Avg Win': positions[positions['pnl'] > 0]['pnl'].mean(),
                'Avg Loss': abs(positions[positions['pnl'] < 0]['pnl'].mean()),
                'Profit Factor': abs(positions[positions['pnl'] > 0]['pnl'].sum() / 
                                   positions[positions['pnl'] < 0]['pnl'].sum())
            }
            
            fig.add_trace(
                go.Bar(x=list(metrics.keys()),
                      y=list(metrics.values()),
                      name="Performance Metrics"),
                row=3, col=2
            )

            # Update layout
            fig.update_layout(
                height=1200,
                showlegend=True,
                template="plotly_dark",
                title=f"Position Analysis Dashboard - {symbol}"
            )

            return fig
        except Exception as e:
            logger.error(f"Error creating position analysis: {str(e)}")
            return None

    def plot_correlation_heatmap(self, symbols: List[str], timeframe: str = 'all') -> go.Figure:
        """Create correlation heatmap for multiple symbols"""
        try:
            # Get position data for each symbol
            symbol_data = {}
            for symbol in symbols:
                positions = pd.DataFrame([p for p in self.db.get_position_history(symbol) if isinstance(p, dict)])
                if not positions.empty:
                    positions['entry_timestamp'] = pd.to_datetime(positions['entry_timestamp'])
                    positions.set_index('entry_timestamp', inplace=True)
                    symbol_data[symbol] = positions['pnl'].resample('ME').sum()

            if not symbol_data:
                return None

            # Create a DataFrame with all symbols' daily returns
            df = pd.DataFrame(symbol_data)
            df.fillna(0, inplace=True)

            # Calculate correlation matrix
            corr_matrix = df.corr()

            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.index,
                colorscale='RdBu',
                zmin=-1,
                zmax=1
            ))

            # Update layout
            fig.update_layout(
                title=f"Symbol Correlation Heatmap ({timeframe})",
                height=800,
                width=800,
                template="plotly_dark"
            )

            return fig
        except Exception as e:
            logger.error(f"Error creating correlation heatmap: {str(e)}")
            return None

    def plot_portfolio_analysis(self, symbols: List[str], timeframe: str = 'all') -> go.Figure:
        """Create portfolio analysis dashboard"""
        try:
            # Get position data for all symbols
            portfolio_data = {}
            for symbol in symbols:
                positions = pd.DataFrame([p for p in self.db.get_position_history(symbol) if isinstance(p, dict)])
                if not positions.empty:
                    positions['entry_timestamp'] = pd.to_datetime(positions['entry_timestamp'])
                    positions.set_index('entry_timestamp', inplace=True)
                    portfolio_data[symbol] = positions

            if not portfolio_data:
                return None

            # Create figure with subplots
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=(
                    'Portfolio Value', 'Asset Allocation',
                    'Rolling Volatility', 'Correlation Matrix',
                    'Drawdown Analysis', 'Risk Contribution'
                ),
                specs=[
                    [{"secondary_y": True}, {"type": "pie"}],
                    [{"secondary_y": True}, {"type": "heatmap"}],
                    [{}, {}]
                ]
            )

            # 1. Portfolio Value
            portfolio_value = pd.Series(dtype=float)
            for symbol, df in portfolio_data.items():
                symbol_value = df['pnl'].cumsum()
                if portfolio_value.empty:
                    portfolio_value = symbol_value
                else:
                    portfolio_value = portfolio_value.add(symbol_value, fill_value=0)

            fig.add_trace(
                go.Scatter(x=portfolio_value.index,
                          y=portfolio_value.values,
                          name="Portfolio Value"),
                row=1, col=1
            )

            # 2. Asset Allocation
            total_positions = {symbol: len(df) for symbol, df in portfolio_data.items()}
            
            fig.add_trace(
                go.Pie(labels=list(total_positions.keys()),
                      values=list(total_positions.values()),
                      name="Asset Allocation"),
                row=1, col=2
            )

            # 3. Rolling Volatility
            window = 30  # 30-day rolling window
            daily_returns = portfolio_value.diff()
            rolling_vol = daily_returns.rolling(window=window).std() * np.sqrt(252)  # Annualized
            
            fig.add_trace(
                go.Scatter(x=rolling_vol.index,
                          y=rolling_vol.values,
                          name="Portfolio Volatility"),
                row=2, col=1
            )

            # 4. Correlation Matrix
            daily_returns_by_symbol = {}
            for symbol, df in portfolio_data.items():
                daily_returns_by_symbol[symbol] = df['pnl'].resample('ME').sum()
            
            returns_df = pd.DataFrame(daily_returns_by_symbol)
            corr_matrix = returns_df.corr()
            
            fig.add_trace(
                go.Heatmap(z=corr_matrix.values,
                          x=corr_matrix.columns,
                          y=corr_matrix.index,
                          colorscale='RdBu',
                          zmin=-1,
                          zmax=1),
                row=2, col=2
            )

            # 5. Drawdown Analysis
            rolling_max = portfolio_value.expanding().max()
            drawdown = (portfolio_value - rolling_max) / rolling_max
            
            fig.add_trace(
                go.Scatter(x=drawdown.index,
                          y=drawdown.values,
                          name="Portfolio Drawdown",
                          fill='tozeroy',
                          fillcolor='rgba(255,0,0,0.2)'),
                row=3, col=1
            )

            # 6. Risk Contribution
            volatilities = {symbol: df['pnl'].std() * np.sqrt(252) 
                          for symbol, df in portfolio_data.items()}
            
            fig.add_trace(
                go.Bar(x=list(volatilities.keys()),
                      y=list(volatilities.values()),
                      name="Risk Contribution"),
                row=3, col=2
            )

            # Update layout
            fig.update_layout(
                height=1200,
                showlegend=True,
                template="plotly_dark",
                title=f"Portfolio Analysis Dashboard ({timeframe})"
            )

            return fig
        except Exception as e:
            logger.error(f"Error creating portfolio analysis: {str(e)}")
            return None

    def plot_backtest_results(self, backtest_data: Dict[str, Any]) -> go.Figure:
        """Create backtest results visualization"""
        try:
            if not backtest_data or 'trades' not in backtest_data or not backtest_data['trades']:
                return None

            # Extract data from backtest results
            trades = pd.DataFrame(backtest_data['trades'])
            trades['timestamp'] = pd.to_datetime(trades['timestamp'])
            trades.set_index('timestamp', inplace=True)

            equity_curve = pd.DataFrame(backtest_data['equity_curve'])
            equity_curve['timestamp'] = pd.to_datetime(equity_curve['timestamp'])
            equity_curve.set_index('timestamp', inplace=True)

            # Create figure with subplots
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=(
                    'Equity Curve', 'Trade Distribution',
                    'Drawdown Analysis', 'Monthly Returns',
                    'Position Sizing', 'Win/Loss Streak'
                ),
                specs=[
                    [{"secondary_y": True}, {}],
                    [{"secondary_y": True}, {"type": "heatmap"}],
                    [{}, {}]
                ]
            )

            # 1. Equity Curve
            fig.add_trace(
                go.Scatter(x=equity_curve.index, 
                          y=equity_curve['equity'],
                          name="Equity"),
                row=1, col=1
            )
            
            # Add drawdown on secondary axis
            drawdown = (equity_curve['equity'] - equity_curve['equity'].expanding().max()) / equity_curve['equity'].expanding().max()
            fig.add_trace(
                go.Scatter(x=drawdown.index, 
                          y=drawdown,
                          name="Drawdown",
                          fill='tozeroy',
                          fillcolor='rgba(255,0,0,0.2)'),
                row=1, col=1,
                secondary_y=True
            )

            # 2. Trade Distribution
            if 'realized_pnl' in trades.columns:
                fig.add_trace(
                    go.Histogram(x=trades['realized_pnl'],
                                name="Trade PnL Distribution",
                                nbinsx=50),
                    row=1, col=2
                )

            # 3. Drawdown Analysis
            underwater = drawdown[drawdown < 0]
            fig.add_trace(
                go.Scatter(x=underwater.index,
                          y=underwater,
                          name="Underwater Plot",
                          fill='tozeroy',
                          fillcolor='rgba(255,0,0,0.2)'),
                row=2, col=1
            )

            # 4. Monthly Returns Heatmap
            if 'realized_pnl' in trades.columns:
                monthly_returns = trades['realized_pnl'].resample('ME').sum().to_frame()
                monthly_returns['year'] = monthly_returns.index.year
                monthly_returns['month'] = monthly_returns.index.month
                pivot_table = monthly_returns.pivot(index='year', 
                                                  columns='month', 
                                                  values='realized_pnl')
                
                if not pivot_table.empty:
                    fig.add_trace(
                        go.Heatmap(z=pivot_table.values,
                                  x=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                                  y=pivot_table.index,
                                  colorscale='RdYlGn',
                                  name="Monthly Returns"),
                        row=2, col=2
                    )

            # 5. Position Sizing
            if 'amount' in trades.columns:
                fig.add_trace(
                    go.Scatter(x=trades.index,
                              y=trades['amount'],
                              name="Position Size",
                              mode='markers'),
                    row=3, col=1
                )

            # 6. Win/Loss Streak Analysis
            if 'realized_pnl' in trades.columns:
                trades['win'] = trades['realized_pnl'] > 0
                streak_data = self._calculate_streaks(trades['win'])
                
                fig.add_trace(
                    go.Bar(x=['Max Win Streak', 'Max Loss Streak'],
                          y=[streak_data['max_win_streak'], 
                             streak_data['max_loss_streak']],
                          name="Win/Loss Streaks"),
                    row=3, col=2
                )

            # Update layout
            fig.update_layout(
                height=1200,
                showlegend=True,
                template="plotly_dark",
                title="Backtest Analysis Dashboard"
            )

            return fig
        except Exception as e:
            logger.error(f"Error creating backtest visualization: {str(e)}")
            return None

    def _calculate_streaks(self, win_series: pd.Series) -> Dict[str, int]:
        """Calculate win/loss streaks from a series of boolean values"""
        try:
            # Initialize variables
            current_streak = 0
            max_win_streak = 0
            max_loss_streak = 0
            current_is_win = None

            # Iterate through the series
            for win in win_series:
                if current_is_win is None:
                    current_is_win = win
                    current_streak = 1
                elif win == current_is_win:
                    current_streak += 1
                else:
                    if current_is_win:
                        max_win_streak = max(max_win_streak, current_streak)
                    else:
                        max_loss_streak = max(max_loss_streak, current_streak)
                    current_streak = 1
                    current_is_win = win

            # Handle the last streak
            if current_is_win:
                max_win_streak = max(max_win_streak, current_streak)
            else:
                max_loss_streak = max(max_loss_streak, current_streak)

            return {
                'max_win_streak': max_win_streak,
                'max_loss_streak': max_loss_streak
            }
        except Exception as e:
            logger.error(f"Error calculating streaks: {str(e)}")
            return {'max_win_streak': 0, 'max_loss_streak': 0}

    def save_analysis_report(self, symbol: str, timeframe: str = 'all', output_dir: str = 'reports'):
        """Generate and save a complete analysis report"""
        try:
            import os
            from datetime import datetime
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate plots
            perf_fig = self.plot_performance_overview(symbol, timeframe)
            risk_fig = self.plot_risk_dashboard(symbol, timeframe)
            pos_fig = self.plot_position_analysis(symbol)
            
            # Save plots
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if perf_fig:
                perf_fig.write_html(os.path.join(output_dir, 
                    f"{symbol.replace('/', '_')}_performance_{timeframe}_{timestamp}.html"))
            if risk_fig:
                risk_fig.write_html(os.path.join(output_dir, 
                    f"{symbol.replace('/', '_')}_risk_{timeframe}_{timestamp}.html"))
            if pos_fig:
                pos_fig.write_html(os.path.join(output_dir, 
                    f"{symbol.replace('/', '_')}_positions_{timeframe}_{timestamp}.html"))
                
            return True
        except Exception as e:
            logger.error(f"Error saving analysis report: {str(e)}")
            return False

    def generate_comprehensive_report(self, symbols: List[str], timeframe: str = 'all', output_dir: str = None) -> Dict[str, go.Figure]:
        """Generate a comprehensive report containing all analytics visualizations"""
        try:
            # Get all visualizations
            report = {}
            for symbol in symbols:
                symbol_report = {
                    'backtest_results': self.plot_backtest_results(symbol, timeframe),
                    'performance_overview': self.plot_performance_overview(symbol, timeframe),
                    'risk_dashboard': self.plot_risk_dashboard(symbol, timeframe),
                    'position_analysis': self.plot_position_analysis(symbol),
                    'correlation_heatmap': self.plot_correlation_heatmap([symbol], timeframe),
                    'portfolio_analysis': self.plot_portfolio_analysis([symbol], timeframe)
                }
                # Filter out None values
                report[symbol] = {k: v for k, v in symbol_report.items() if v is not None}

            # Save to files if output directory is specified
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                for symbol, symbol_report in report.items():
                    symbol_dir = os.path.join(output_dir, symbol)
                    os.makedirs(symbol_dir, exist_ok=True)
                    for name, fig in symbol_report.items():
                        fig.write_html(os.path.join(symbol_dir, f"{name}.html"))

            return report
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {str(e)}")
            return {}

    def plot_backtest_results(self, symbol: str, timeframe: str = 'all') -> go.Figure:
        """Create backtest results visualization"""
        try:
            # Get equity curve data
            equity_curve = pd.DataFrame([e for e in self.db.get_equity_history(symbol, timeframe) if isinstance(e, dict)])
            if equity_curve.empty:
                return None

            # Convert timestamps and set index
            equity_curve['timestamp'] = pd.to_datetime(equity_curve['timestamp'])
            equity_curve.set_index('timestamp', inplace=True)

            # Create figure
            fig = go.Figure()

            # Add equity curve
            fig.add_trace(
                go.Scatter(x=equity_curve.index,
                          y=equity_curve['equity'],
                          name="Equity Curve",
                          line=dict(color='blue'))
            )
            
            # Add drawdown on secondary axis
            drawdown = (equity_curve['equity'] - equity_curve['equity'].expanding().max()) / equity_curve['equity'].expanding().max()
            fig.add_trace(
                go.Scatter(x=drawdown.index, 
                          y=drawdown,
                          name="Drawdown",
                          yaxis="y2",
                          fill='tozeroy',
                          fillcolor='rgba(255,0,0,0.2)',
                          line=dict(color='red'))
            )

            # Update layout
            fig.update_layout(
                title=f"Backtest Results - {symbol} ({timeframe})",
                yaxis=dict(title="Equity"),
                yaxis2=dict(title="Drawdown",
                           overlaying="y",
                           side="right",
                           range=[-1, 0.1]),  # Drawdown typically from -100% to +10%
                template="plotly_dark",
                showlegend=True
            )

            return fig
        except Exception as e:
            logger.error(f"Error creating backtest visualization: {str(e)}")
            return None
