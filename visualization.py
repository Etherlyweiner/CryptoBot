import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict

@st.cache_data
def create_price_chart(df: pd.DataFrame, symbol: str):
    """Create an interactive price chart with volume."""
    fig = go.Figure()
    
    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='OHLC'
    ))
    
    # Volume bars
    fig.add_trace(go.Bar(
        x=df['timestamp'],
        y=df['volume'],
        name='Volume',
        yaxis='y2',
        opacity=0.3
    ))
    
    # Layout
    fig.update_layout(
        title=f'{symbol} Price and Volume',
        yaxis_title='Price',
        yaxis2=dict(
            title='Volume',
            overlaying='y',
            side='right'
        ),
        xaxis_title='Date',
        height=600
    )
    
    return fig

@st.cache_data
def create_volume_bar_chart(volume_data: Dict[str, float]):
    """Create a bar chart of trading volumes."""
    df = pd.DataFrame(list(volume_data.items()), columns=['Symbol', 'Volume'])
    fig = px.bar(
        df,
        x='Symbol',
        y='Volume',
        title='Top Trading Volumes',
        height=400
    )
    fig.update_layout(xaxis_tickangle=-45)
    return fig

@st.cache_data
def format_price_change(current: float, previous: float) -> tuple:
    """Format price change with color coding."""
    if previous:
        change = ((current - previous) / previous) * 100
        color = 'green' if change >= 0 else 'red'
        return f"{change:.2f}%", color
    return "N/A", 'gray'
