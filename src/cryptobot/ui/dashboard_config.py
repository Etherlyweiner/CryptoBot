"""Dashboard configuration and layout"""
import streamlit as st
import pandas as pd
from typing import Dict, List
import plotly.graph_objects as go
from datetime import datetime, timedelta

def configure_page():
    """Configure the Streamlit page settings"""
    st.set_page_config(
        page_title="CryptoBot Dashboard",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def render_overview(stats: Dict):
    """Render the overview section"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Daily P&L", f"{stats.get('daily_pnl', 0):.2f} SOL")
    with col2:
        st.metric("Win Rate", f"{stats.get('win_rate', 0):.1f}%")
    with col3:
        st.metric("Active Positions", stats.get('active_positions', 0))
    with col4:
        st.metric("Daily Trades", stats.get('daily_trades', 0))

def render_positions(positions: List[Dict]):
    """Render active positions table"""
    if not positions:
        st.info("No active positions")
        return
        
    df = pd.DataFrame(positions)
    st.dataframe(
        df[['token', 'entry_price', 'current_price', 'size', 'pnl', 'time_open']],
        hide_index=True
    )

def render_price_chart(price_history: List[Dict]):
    """Render price chart with technical indicators"""
    if not price_history:
        return
        
    df = pd.DataFrame(price_history)
    
    fig = go.Figure()
    
    # Add candlestick chart
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name="OHLC"
    ))
    
    # Add volume bars
    fig.add_trace(go.Bar(
        x=df['timestamp'],
        y=df['volume'],
        name="Volume",
        yaxis="y2"
    ))
    
    # Update layout
    fig.update_layout(
        title="Price Chart",
        yaxis_title="Price",
        yaxis2=dict(
            title="Volume",
            overlaying="y",
            side="right"
        ),
        xaxis_rangeslider_visible=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_trade_history(trades: List[Dict]):
    """Render trade history table"""
    if not trades:
        st.info("No trade history available")
        return
        
    df = pd.DataFrame(trades)
    st.dataframe(
        df[['token', 'entry_price', 'exit_price', 'size', 'pnl', 'duration', 'reason']],
        hide_index=True
    )

def render_risk_metrics(risk_metrics: Dict):
    """Render risk metrics"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Max Drawdown", f"{risk_metrics.get('max_drawdown', 0):.2f}%")
        st.metric("Sharpe Ratio", f"{risk_metrics.get('sharpe_ratio', 0):.2f}")
        
    with col2:
        st.metric("Win/Loss Ratio", f"{risk_metrics.get('win_loss_ratio', 0):.2f}")
        st.metric("Avg Trade Duration", f"{risk_metrics.get('avg_duration', '0m')}")
