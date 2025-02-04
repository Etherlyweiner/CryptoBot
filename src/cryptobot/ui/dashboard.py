"""Main dashboard for the trading bot"""
import streamlit as st
import asyncio
from typing import Dict, List
import json
from datetime import datetime, timedelta

from .dashboard_config import (
    configure_page,
    render_overview,
    render_positions,
    render_price_chart,
    render_trade_history,
    render_risk_metrics
)

class Dashboard:
    def __init__(self, bot):
        self.bot = bot
        self.last_update = datetime.now()
        configure_page()
        
    async def update_data(self):
        """Update dashboard data"""
        try:
            # Get active positions
            positions = await self.bot.get_active_positions()
            
            # Get trade history
            trade_history = await self.bot.get_trade_history()
            
            # Calculate statistics
            stats = self._calculate_statistics(positions, trade_history)
            
            # Get risk metrics
            risk_metrics = self._calculate_risk_metrics(trade_history)
            
            return {
                'positions': positions,
                'trade_history': trade_history,
                'stats': stats,
                'risk_metrics': risk_metrics
            }
            
        except Exception as e:
            st.error(f"Error updating dashboard: {str(e)}")
            return None
            
    def _calculate_statistics(self, positions: List[Dict], trades: List[Dict]) -> Dict:
        """Calculate trading statistics"""
        stats = {
            'daily_pnl': 0,
            'win_rate': 0,
            'active_positions': len(positions),
            'daily_trades': 0
        }
        
        if not trades:
            return stats
            
        # Calculate daily P&L
        today = datetime.now().date()
        daily_trades = [t for t in trades if t['exit_time'].date() == today]
        stats['daily_pnl'] = sum(t['pnl'] for t in daily_trades)
        stats['daily_trades'] = len(daily_trades)
        
        # Calculate win rate
        winning_trades = [t for t in trades if t['pnl'] > 0]
        stats['win_rate'] = (len(winning_trades) / len(trades)) * 100
        
        return stats
        
    def _calculate_risk_metrics(self, trades: List[Dict]) -> Dict:
        """Calculate risk metrics"""
        if not trades:
            return {
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'win_loss_ratio': 0,
                'avg_duration': '0m'
            }
            
        # Calculate metrics
        pnl_series = [t['pnl'] for t in trades]
        durations = [(t['exit_time'] - t['entry_time']).total_seconds() / 60 for t in trades]
        
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]
        
        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = abs(sum(t['pnl'] for t in losing_trades) / len(losing_trades)) if losing_trades else 0
        
        return {
            'max_drawdown': self._calculate_max_drawdown(pnl_series),
            'sharpe_ratio': self._calculate_sharpe_ratio(pnl_series),
            'win_loss_ratio': avg_win / avg_loss if avg_loss != 0 else 0,
            'avg_duration': f"{sum(durations) / len(durations):.1f}m"
        }
        
    def _calculate_max_drawdown(self, pnl_series: List[float]) -> float:
        """Calculate maximum drawdown"""
        peak = float('-inf')
        max_dd = 0
        
        for pnl in pnl_series:
            if pnl > peak:
                peak = pnl
            dd = (peak - pnl) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
            
        return max_dd * 100
        
    def _calculate_sharpe_ratio(self, pnl_series: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if not pnl_series:
            return 0
            
        returns = [p / abs(p) if p != 0 else 0 for p in pnl_series]
        avg_return = sum(returns) / len(returns)
        std_dev = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
        
        if std_dev == 0:
            return 0
            
        return (avg_return - risk_free_rate) / std_dev
        
    async def run(self):
        """Run the dashboard"""
        st.title("CryptoBot Dashboard")
        
        # Add settings to sidebar
        with st.sidebar:
            st.header("Settings")
            update_interval = st.slider("Update Interval (seconds)", 1, 60, 5)
            
        # Main content
        while True:
            if datetime.now() - self.last_update >= timedelta(seconds=update_interval):
                data = await self.update_data()
                if data:
                    render_overview(data['stats'])
                    
                    st.header("Active Positions")
                    render_positions(data['positions'])
                    
                    st.header("Price Chart")
                    if data['positions']:
                        token = data['positions'][0]['token']
                        price_history = await self.bot.get_price_history(token)
                        render_price_chart(price_history)
                        
                    st.header("Trade History")
                    render_trade_history(data['trade_history'])
                    
                    st.header("Risk Metrics")
                    render_risk_metrics(data['risk_metrics'])
                    
                self.last_update = datetime.now()
                
            await asyncio.sleep(1)
