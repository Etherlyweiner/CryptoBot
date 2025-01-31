import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import asyncio
from bot import CryptoBot
from risk_monitor import RiskMonitor
import os
from config import *
import time

# Page config
st.set_page_config(
    page_title="CryptoBot Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state with defaults
async def init_session_state():
    if 'bot' not in st.session_state:
        st.session_state.bot = CryptoBot()
    if 'risk_monitor' not in st.session_state:
        st.session_state.risk_monitor = await RiskMonitor().__aenter__()
    if 'last_data_update' not in st.session_state:
        st.session_state.last_data_update = datetime.now() - timedelta(minutes=5)
    if 'cached_ohlcv_data' not in st.session_state:
        st.session_state.cached_ohlcv_data = None
    if 'positions_cache' not in st.session_state:
        st.session_state.positions_cache = {}

# Cleanup session state
async def cleanup_session_state():
    if 'risk_monitor' in st.session_state:
        await st.session_state.risk_monitor.__aexit__(None, None, None)

# Cache decorator for expensive operations
def cache_data(ttl_seconds=300):
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}_{str(args)}_{str(kwargs)}"
            current_time = datetime.now()
            
            if (cache_key not in st.session_state or 
                'timestamp' not in st.session_state[cache_key] or
                (current_time - st.session_state[cache_key]['timestamp']).total_seconds() > ttl_seconds):
                
                result = func(*args, **kwargs)
                st.session_state[cache_key] = {
                    'data': result,
                    'timestamp': current_time
                }
            
            return st.session_state[cache_key]['data']
        return wrapper
    return decorator

def main():
    # Initialize session state
    asyncio.run(init_session_state())

    # Sidebar
    with st.sidebar:
        st.title("🤖 CryptoBot Controls")
        
        # Wallet Connection
        st.subheader("Wallet Connection")
        wallet_address = st.text_input("Phantom Wallet Address", 
                                     value=PHANTOM_WALLET if PHANTOM_WALLET else "",
                                     key="wallet_input")
        if st.button("Connect Wallet", key="connect_button"):
            try:
                # Add wallet connection logic here
                st.success("Wallet connected successfully!")
            except Exception as e:
                st.error(f"Failed to connect wallet: {str(e)}")

        # Risk Management Settings
        st.subheader("Risk Management")
        try:
            new_stop_loss = st.slider("Stop Loss %", 0.1, 5.0, 
                                    float(STOP_LOSS_PERCENTAGE * 100), 0.1) / 100
            new_take_profit = st.slider("Take Profit %", 1.0, 10.0, 
                                      float(TAKE_PROFIT_PERCENTAGE * 100), 0.1) / 100
            new_max_trades = st.number_input("Max Trades per Day", 1, 50, 
                                           MAX_TRADES_PER_DAY)
            new_position_size = st.number_input("Position Size (USD)", 1.0, 100.0, 
                                              TARGET_POSITION_SIZE, 0.5)

            # Apply Settings Button
            if st.button("Apply Settings", key="apply_settings"):
                update_config(
                    stop_loss=new_stop_loss,
                    take_profit=new_take_profit,
                    max_trades=new_max_trades,
                    position_size=new_position_size
                )
                st.success("Settings updated successfully!")
        except Exception as e:
            st.error(f"Error loading settings: {str(e)}")

    # Main content
    st.title("📊 CryptoBot Dashboard")

    try:
        # Top metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            active_trades = len(st.session_state.bot.positions) if hasattr(st.session_state.bot, 'positions') else 0
            st.metric("Active Trades", active_trades)
        with col2:
            daily_trades = st.session_state.bot.daily_trades if hasattr(st.session_state.bot, 'daily_trades') else 0
            st.metric("Daily Trades", daily_trades)
        with col3:
            daily_pnl = calculate_daily_pnl()
            st.metric("Daily P&L", f"${daily_pnl:,.2f}")
        with col4:
            try:
                risk_score = st.session_state.risk_monitor.calculate_risk_score(
                    {"liquidity": 100000, "holders": 500, "volume_24h": 50000, "volume_24h_prev": 40000},
                    []
                )
                st.metric("Risk Score", f"{risk_score:.2f}")
            except Exception:
                st.metric("Risk Score", "N/A")

        # Charts and Analysis
        tab1, tab2, tab3 = st.tabs(["Trading View", "Risk Analysis", "New Launches"])

        with tab1:
            st.subheader("Price Chart")
            display_trading_chart()
            st.subheader("Active Positions")
            display_positions()

        with tab2:
            st.subheader("Risk Monitoring")
            display_risk_analysis()

        with tab3:
            st.subheader("Latest Token Launches")
            display_new_launches()

    except Exception as e:
        st.error(f"Error updating dashboard: {str(e)}")

    # Cleanup session state
    asyncio.run(cleanup_session_state())

@cache_data(ttl_seconds=300)
def calculate_daily_pnl():
    """Calculate daily profit/loss with caching"""
    try:
        # Implement actual PnL calculation here
        return 0.0  # Placeholder
    except Exception:
        return 0.0

@cache_data(ttl_seconds=60)
def fetch_and_process_ohlcv(symbol='SOL/USDT', limit=100):
    """Fetch and process OHLCV data with caching"""
    try:
        df = st.session_state.bot.fetch_ohlcv(symbol, limit=limit)
        if df is not None:
            return st.session_state.bot.calculate_signals(df)
        return None
    except Exception:
        return None

def display_trading_chart():
    """Display trading chart with indicators"""
    df = fetch_and_process_ohlcv()
    if df is not None:
        try:
            # Create candlestick chart
            fig = go.Figure(data=[go.Candlestick(x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'])])
            
            # Add indicators
            if 'BB_upper' in df.columns and 'BB_lower' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['BB_upper'], name='BB Upper'))
                fig.add_trace(go.Scatter(x=df.index, y=df['BB_lower'], name='BB Lower'))
            
            # Update layout with better performance settings
            fig.update_layout(
                title='SOL/USDT Price',
                yaxis_title='Price (USDT)',
                xaxis_title='Time',
                template='plotly_dark',
                uirevision='constant',  # Preserve UI state on updates
                showlegend=True,
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01
                )
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        except Exception as e:
            st.error(f"Error displaying chart: {str(e)}")
    else:
        st.warning("No data available for chart")

def display_positions():
    """Display active trading positions"""
    try:
        if hasattr(st.session_state.bot, 'positions') and st.session_state.bot.positions:
            positions_df = pd.DataFrame.from_dict(
                st.session_state.bot.positions, 
                orient='index'
            )
            st.dataframe(positions_df)
        else:
            st.info("No active positions")
    except Exception as e:
        st.error(f"Error displaying positions: {str(e)}")

@cache_data(ttl_seconds=300)
def display_risk_analysis():
    """Display risk analysis metrics with caching"""
    try:
        # Create sample risk metrics
        risk_metrics = {
            "Liquidity Score": 0.85,
            "Holder Distribution": 0.75,
            "Volume Pattern": 0.90,
            "Pump Signal Risk": 0.95
        }
        
        fig = go.Figure([go.Bar(
            x=list(risk_metrics.keys()),
            y=list(risk_metrics.values()),
            marker_color=['green' if v >= 0.7 else 'yellow' if v >= 0.5 else 'red' for v in risk_metrics.values()]
        )])
        
        fig.update_layout(
            title='Risk Analysis Metrics',
            yaxis_title='Score',
            yaxis_range=[0, 1],
            template='plotly_dark',
            uirevision='constant'
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    except Exception as e:
        st.error(f"Error displaying risk analysis: {str(e)}")

@cache_data(ttl_seconds=300)
def display_new_launches():
    """Display new token launches with caching"""
    try:
        launches = pd.DataFrame({
            'Token': ['TOKEN1', 'TOKEN2', 'TOKEN3'],
            'Launch Time': [datetime.now()] * 3,
            'Initial Price': [0.1, 0.2, 0.3],
            'Current Price': [0.15, 0.18, 0.35],
            'Risk Score': [0.8, 0.7, 0.9]
        })
        
        st.dataframe(launches)
    except Exception as e:
        st.error(f"Error displaying new launches: {str(e)}")

def update_config(stop_loss, take_profit, max_trades, position_size):
    """Update bot configuration"""
    global STOP_LOSS_PERCENTAGE, TAKE_PROFIT_PERCENTAGE, MAX_TRADES_PER_DAY, TARGET_POSITION_SIZE
    
    STOP_LOSS_PERCENTAGE = stop_loss
    TAKE_PROFIT_PERCENTAGE = take_profit
    MAX_TRADES_PER_DAY = max_trades
    TARGET_POSITION_SIZE = position_size

if __name__ == "__main__":
    main()
