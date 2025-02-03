"""
UI Components for the CryptoBot Dashboard
"""

import streamlit as st
import plotly.graph_objects as go
from typing import Dict, List, Optional
import pandas as pd
import os

def render_header():
    """Render the dashboard header with logo and title."""
    col1, col2 = st.columns([1, 4])
    with col1:
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "assets", "logo.png")
        st.image(logo_path, width=100)
    with col2:
        st.title("Solana Trading Bot")
        st.markdown("---")

def render_metrics_card(title: str, value: str, delta: Optional[float] = None):
    """Render a metric card with optional delta indicator."""
    st.metric(
        label=title,
        value=value,
        delta=f"{delta:+.2f}%" if delta is not None else None,
        delta_color="normal"
    )

def render_wallet_section(balance: float, recent_transactions: List[Dict]):
    """Render wallet information section."""
    st.subheader("📊 Wallet Overview")
    col1, col2 = st.columns(2)
    
    with col1:
        render_metrics_card("SOL Balance", f"◎ {balance:.4f}")
    
    with col2:
        st.markdown("### Recent Transactions")
        if recent_transactions:
            df = pd.DataFrame(recent_transactions)
            st.dataframe(df, hide_index=True)
        else:
            st.info("No recent transactions")

def render_trading_controls(trading_enabled: bool):
    """Render trading control buttons."""
    st.subheader("🎮 Trading Controls")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Start Trading" if not trading_enabled else "Stop Trading"):
            # Toggle trading state
            return not trading_enabled
    
    with col2:
        if st.button("Emergency Stop", type="secondary"):
            return False
    
    with col3:
        st.download_button(
            "Export Trading History",
            data="",  # TODO: Add CSV export
            file_name="trading_history.csv",
            mime="text/csv",
        )
    
    return trading_enabled

def render_performance_chart(performance_data: pd.DataFrame):
    """Render trading performance chart."""
    st.subheader("📈 Performance")
    
    if performance_data.empty:
        st.info("No performance data available yet")
        return
        
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=performance_data.index,
            y=performance_data["portfolio_value"],
            mode="lines",
            name="Portfolio Value",
            line=dict(color="#00ff00", width=2)
        )
    )
    
    fig.update_layout(
        template="plotly_dark",
        xaxis_title="Date",
        yaxis_title="Value (SOL)",
        height=400,
        margin=dict(l=0, r=0, t=30, b=0)
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_active_positions(positions: List[Dict]):
    """Render active trading positions."""
    st.subheader("🎯 Active Positions")
    
    if not positions:
        st.info("No active positions")
        return
        
    df = pd.DataFrame(positions)
    st.dataframe(
        df,
        column_config={
            "token": "Token",
            "entry_price": st.column_config.NumberColumn(
                "Entry Price",
                format="$%.2f"
            ),
            "current_price": st.column_config.NumberColumn(
                "Current Price",
                format="$%.2f"
            ),
            "pnl": st.column_config.NumberColumn(
                "PnL %",
                format="%.2f%%"
            )
        },
        hide_index=True
    )

def render_settings_section(config: Dict):
    """Render bot settings section."""
    st.subheader("⚙️ Settings")
    
    with st.expander("Trading Parameters"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.number_input(
                "Position Size (SOL)",
                min_value=0.1,
                max_value=10.0,
                value=float(config.get("POSITION_SIZE_SOL", 0.1)),
                step=0.1
            )
            
            st.number_input(
                "Stop Loss (%)",
                min_value=1,
                max_value=20,
                value=int(config.get("STOP_LOSS_PERCENT", 5)),
                step=1
            )
        
        with col2:
            st.number_input(
                "Take Profit (%)",
                min_value=1,
                max_value=50,
                value=int(config.get("TAKE_PROFIT_PERCENT", 10)),
                step=1
            )
            
            st.number_input(
                "Max Positions",
                min_value=1,
                max_value=10,
                value=int(config.get("MAX_POSITIONS", 3)),
                step=1
            )
    
    with st.expander("Network Settings"):
        st.selectbox(
            "Solana Network",
            options=["mainnet-beta", "devnet"],
            index=0 if config.get("SOLANA_NETWORK") == "mainnet-beta" else 1
        )
        
        st.text_input(
            "RPC URL",
            value=config.get("SOLANA_RPC_URL", ""),
            type="password"
        )
