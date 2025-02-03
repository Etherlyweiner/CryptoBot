"""
CryptoBot Dashboard Application
"""

import streamlit as st
import asyncio
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
from cryptobot.trading.engine import TradingEngine
import pandas as pd

# Initialize components
config_manager = ConfigurationManager()
metrics_collector = MetricsCollector()
logger = BotLogger()
trading_engine = TradingEngine()

# Initialize session state
if 'trading_task' not in st.session_state:
    st.session_state.trading_task = None

# Page config
st.set_page_config(
    page_title="CryptoBot Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

async def start_trading():
    """Start the trading engine."""
    try:
        await trading_engine.initialize()
        await trading_engine.start()
    except Exception as e:
        logger.error(f"Failed to start trading: {str(e)}")
        st.error("Failed to start trading. Check logs for details.")

def stop_trading():
    """Stop the trading engine."""
    if trading_engine:
        trading_engine.stop()
        logger.info("Trading stopped")

def main():
    """Main dashboard application."""
    # Render header
    render_header()
    
    # Sidebar
    with st.sidebar:
        st.subheader("🔄 Bot Status")
        trading_enabled = st.toggle("Trading Enabled", value=False)
        
        if trading_enabled:
            if not st.session_state.trading_task:
                st.session_state.trading_task = asyncio.create_task(start_trading())
            st.success("Bot is running")
        else:
            if st.session_state.trading_task:
                stop_trading()
                st.session_state.trading_task = None
            st.warning("Bot is stopped")
            
        st.markdown("---")
        
        # Quick stats
        st.subheader("📊 Quick Stats")
        metrics = metrics_collector.get_metrics()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Trades", metrics['trades']['total_executed'])
            st.metric("Active Positions", metrics['trades']['active_positions'])
        with col2:
            st.metric("Portfolio Value", f"{metrics['trades']['portfolio_value']:.2f} SOL")
            st.metric("Success Rate", f"{100 - (metrics['errors']['failed_trades'] / max(1, metrics['trades']['total_executed']) * 100):.1f}%")
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Performance chart
        st.subheader("📈 Performance")
        # TODO: Implement actual performance data
        performance_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=30, freq='D'),
            'portfolio_value': [100 + i * 0.5 + (i * i * 0.1) for i in range(30)]
        })
        render_performance_chart(performance_data)
        
        # Active positions
        st.subheader("🎯 Active Positions")
        positions = trading_engine.get_positions() if trading_enabled else []
        render_active_positions(positions)
    
    with col2:
        # Wallet section
        st.subheader("👛 Wallet")
        render_wallet_section(
            balance=trading_engine.get_portfolio_value() if trading_enabled else 0.0,
            recent_transactions=[]  # TODO: Implement transaction history
        )
        
        # Trading controls
        st.subheader("🎮 Controls")
        render_trading_controls(trading_enabled)
        
        # Settings
        st.subheader("⚙️ Settings")
        render_settings_section(config_manager.get_all_config())

if __name__ == "__main__":
    main()
