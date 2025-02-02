"""Real-time monitoring dashboard for CryptoBot."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from decimal import Decimal
import numpy as np
from datetime import datetime, timedelta
from database import Session, Trade, RiskMetricsHistory
import logging

logger = logging.getLogger('MonitoringDashboard')

def main():
    """Main dashboard function."""
    st.set_page_config(
        page_title="CryptoBot Monitor",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("CryptoBot Trading Monitor")
    
    # Initialize database session
    session = Session()
    
    try:
        # Get recent trades
        trades_df = pd.read_sql(
            session.query(Trade)
            .filter(Trade.timestamp >= datetime.now() - timedelta(days=7))
            .statement,
            session.bind
        )
        
        # Get risk metrics
        metrics_df = pd.read_sql(
            session.query(RiskMetricsHistory)
            .filter(RiskMetricsHistory.timestamp >= datetime.now() - timedelta(days=7))
            .statement,
            session.bind
        )
        
        # Layout
        col1, col2 = st.columns(2)
        
        with col1:
            display_performance_metrics(trades_df, metrics_df)
            
        with col2:
            display_risk_metrics(metrics_df)
            
        # Trading activity
        st.subheader("Recent Trading Activity")
        display_trading_activity(trades_df)
        
        # Risk evolution
        st.subheader("Risk Metrics Evolution")
        display_risk_evolution(metrics_df)
        
    finally:
        session.close()
        
def display_performance_metrics(trades_df: pd.DataFrame, metrics_df: pd.DataFrame):
    """Display key performance metrics."""
    st.subheader("Performance Metrics")
    
    # Calculate metrics
    if not trades_df.empty:
        total_trades = len(trades_df)
        profitable_trades = len(trades_df[trades_df['profit_loss'] > 0])
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        total_profit = trades_df['profit_loss'].sum()
        max_drawdown = metrics_df['current_drawdown'].max() if not metrics_df.empty else 0
        
        # Display metrics
        cols = st.columns(3)
        cols[0].metric("Total Trades", total_trades)
        cols[1].metric("Win Rate", f"{win_rate:.1%}")
        cols[2].metric("Total Profit", f"${total_profit:,.2f}")
        
        cols = st.columns(3)
        cols[0].metric("Max Drawdown", f"{max_drawdown:.1%}")
        cols[1].metric("Profit Factor", 
                      f"{metrics_df['profit_factor'].iloc[-1]:.2f}" 
                      if not metrics_df.empty else "N/A")
        cols[2].metric("Sharpe Ratio",
                      f"{metrics_df['sharpe_ratio'].iloc[-1]:.2f}"
                      if not metrics_df.empty else "N/A")
        
def display_risk_metrics(metrics_df: pd.DataFrame):
    """Display current risk metrics."""
    st.subheader("Current Risk Status")
    
    if not metrics_df.empty:
        latest = metrics_df.iloc[-1]
        
        # Create risk gauge
        exposure_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=latest['total_exposure'] * 100,
            title={'text': "Total Exposure (%)"},
            gauge={'axis': {'range': [0, 100]},
                  'bar': {'color': "darkblue"},
                  'steps': [
                      {'range': [0, 30], 'color': "lightgreen"},
                      {'range': [30, 70], 'color': "yellow"},
                      {'range': [70, 100], 'color': "red"}
                  ]}
        ))
        
        st.plotly_chart(exposure_fig, use_container_width=True)
        
        # Risk metrics
        cols = st.columns(3)
        cols[0].metric("Current Drawdown", f"{latest['current_drawdown']:.1%}")
        cols[1].metric("Daily PnL", f"${latest['daily_pnl']:,.2f}")
        cols[2].metric("Win Rate", f"{latest['win_rate']:.1%}")
        
def display_trading_activity(trades_df: pd.DataFrame):
    """Display recent trading activity."""
    if not trades_df.empty:
        trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
        trades_df = trades_df.sort_values('timestamp', ascending=False)
        
        # Create candlestick chart
        fig = make_subplots(rows=2, cols=1,
                           shared_xaxes=True,
                           vertical_spacing=0.03,
                           subplot_titles=('Price', 'Volume'),
                           row_heights=[0.7, 0.3])
        
        # Add trades
        fig.add_trace(
            go.Scatter(
                x=trades_df['timestamp'],
                y=trades_df['entry_price'],
                mode='markers',
                name='Trades',
                marker=dict(
                    size=8,
                    color=trades_df['profit_loss'].apply(
                        lambda x: 'green' if x > 0 else 'red'
                    )
                )
            ),
            row=1, col=1
        )
        
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)
        
        # Recent trades table
        st.dataframe(
            trades_df[['timestamp', 'symbol', 'side', 'entry_price',
                      'exit_price', 'profit_loss']].head(10)
        )
        
def display_risk_evolution(metrics_df: pd.DataFrame):
    """Display risk metrics evolution."""
    if not metrics_df.empty:
        metrics_df['timestamp'] = pd.to_datetime(metrics_df['timestamp'])
        
        # Create multi-line chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=metrics_df['timestamp'],
            y=metrics_df['total_exposure'],
            name='Total Exposure',
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=metrics_df['timestamp'],
            y=metrics_df['current_drawdown'],
            name='Drawdown',
            line=dict(color='red')
        ))
        
        fig.add_trace(go.Scatter(
            x=metrics_df['timestamp'],
            y=metrics_df['win_rate'],
            name='Win Rate',
            line=dict(color='green')
        ))
        
        fig.update_layout(
            title="Risk Metrics Evolution",
            xaxis_title="Time",
            yaxis_title="Value",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
if __name__ == "__main__":
    main()
