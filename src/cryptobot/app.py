"""
CryptoBot Dashboard Application
"""

import streamlit as st
from cryptobot.ui.components import (
    render_header,
    render_wallet_section,
    render_trading_controls,
    render_performance_chart,
    render_active_positions,
    render_settings_section
)
from cryptobot.config.manager import ConfigurationManager
from cryptobot.monitoring.metrics import MetricsCollector
from cryptobot.monitoring.logger import BotLogger
import pandas as pd

# Initialize components
config_manager = ConfigurationManager()
metrics_collector = MetricsCollector()
logger = BotLogger()

# Page config
st.set_page_config(
    page_title="CryptoBot Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main dashboard application."""
    # Render header
    render_header()
    
    # Sidebar
    with st.sidebar:
        st.subheader("🔄 Bot Status")
        trading_enabled = st.toggle("Trading Enabled", value=False)
        
        if trading_enabled:
            st.success("Bot is running")
        else:
            st.warning("Bot is stopped")
            
        st.markdown("---")
        
        # Quick stats
        st.subheader("📊 Quick Stats")
        metrics = metrics_collector.get_metrics()
        
        st.metric(
            "Total Trades",
            f"{metrics['trades']['total_executed']:.0f}",
            f"{metrics['trades']['total_volume']:.2f} SOL"
        )
        
        st.metric(
            "Active Positions",
            f"{metrics['trades']['active_positions']:.0f}"
        )
        
        st.metric(
            "Portfolio Value",
            f"◎ {metrics['trades']['portfolio_value']:.4f}"
        )
        
        st.markdown("---")
        
        # Error stats
        st.subheader("⚠️ Errors")
        st.metric(
            "Total Errors",
            f"{metrics['errors']['total']:.0f}",
            f"{metrics['errors']['failed_trades']:.0f} failed trades"
        )
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Performance chart
        performance_data = pd.DataFrame({
            'portfolio_value': [100, 105, 103, 108, 110, 107, 112],
            'timestamp': pd.date_range(start='2024-01-01', periods=7, freq='D')
        }).set_index('timestamp')
        
        render_performance_chart(performance_data)
        
        # Active positions
        positions = [
            {
                'token': 'SOL/USDC',
                'entry_price': 100.50,
                'current_price': 105.75,
                'pnl': 5.22
            }
        ]
        render_active_positions(positions)
    
    with col2:
        # Wallet section
        render_wallet_section(
            balance=10.5,
            recent_transactions=[
                {
                    'type': 'BUY',
                    'token': 'SOL/USDC',
                    'amount': 0.5,
                    'price': 100.50
                }
            ]
        )
        
        # Trading controls
        trading_enabled = render_trading_controls(trading_enabled)
    
    # Settings section
    render_settings_section(config_manager.get_all_config())

if __name__ == "__main__":
    main()
