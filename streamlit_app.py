import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from functools import wraps
import json
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from config import *
from database import Database
import plotly.graph_objects as go
import plotly.express as px

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize database
db = Database()

# Initialize page config with optimized settings
st.set_page_config(
    page_title="CryptoBot Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Initialize session state for performance tracking
if 'request_times' not in st.session_state:
    st.session_state.request_times = []

# Performance monitoring decorator
def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            st.session_state.request_times.append(duration)
            # Keep only last 100 measurements
            if len(st.session_state.request_times) > 100:
                st.session_state.request_times = st.session_state.request_times[-100:]
            if duration > 1.0:  # Log slow operations
                logger.warning(f"Performance warning: {func.__name__} took {duration:.2f} seconds")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
    return wrapper

# Optimized API client with retries
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
def api_request(url, params=None, timeout=10):
    """Centralized API request handler with retries and proper error handling"""
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API Error: {str(e)}")
        raise

# Cache crypto data for 1 minute
@st.cache_data(ttl=60, show_spinner=False)
def get_crypto_data(symbol="bitcoin"):
    """Fetch crypto data with improved caching and error handling"""
    try:
        price_url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": symbol,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_24hr_vol": "true",
            "include_market_cap": "true"
        }
        
        data = api_request(price_url, params=params)
        if not data or symbol not in data:
            logger.error(f"Invalid data received for {symbol}")
            return None
            
        return data[symbol]
    except RetryError:
        st.error("Failed to fetch crypto data after multiple retries")
        return None
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        st.error("An unexpected error occurred while fetching data")
        return None

# Cache trending coins for 5 minutes
@st.cache_data(ttl=300, show_spinner=False)
def get_trending_coins():
    """Fetch trending coins with improved caching and error handling"""
    try:
        data = api_request("https://api.coingecko.com/api/v3/search/trending")
        if not data or 'coins' not in data:
            logger.error("Invalid trending coins data received")
            return []
            
        trending = []
        for coin in data.get('coins', [])[:5]:
            item = coin.get('item', {})
            if not item:
                continue
                
            trending.append({
                'name': item.get('name', 'Unknown'),
                'symbol': item.get('symbol', '???').upper(),
                'market_cap_rank': item.get('market_cap_rank', 'N/A'),
                'price_btc': item.get('price_btc', 0.0)
            })
        
        return trending
    except RetryError:
        st.error("Failed to fetch trending coins after multiple retries")
        return []
    except Exception as e:
        logger.error(f"Error fetching trending coins: {str(e)}")
        st.error("An unexpected error occurred while fetching trending coins")
        return []

@measure_time
def main():
    try:
        # Title and description
        st.title("🤖 CryptoBot Dashboard")
        st.markdown("---")
        
        # Create columns for layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Main content with error handling
            btc_data = get_crypto_data("bitcoin")
            if btc_data:
                st.metric(
                    "Bitcoin Price",
                    f"${btc_data.get('usd', 0):,.2f}",
                    f"{btc_data.get('usd_24h_change', 0):.2f}%"
                )
                
                # Market data in expandable section
                with st.expander("Market Data", expanded=True):
                    st.write(f"24h Volume: ${btc_data.get('usd_24h_vol', 0):,.0f}")
                    st.write(f"Market Cap: ${btc_data.get('usd_market_cap', 0):,.0f}")
        
        with col2:
            # Trending coins with error handling
            st.subheader("🔥 Trending Coins")
            trending = get_trending_coins()
            
            if trending:
                for coin in trending:
                    st.write(f"{coin['name']} ({coin['symbol']})")
                    st.write(f"Rank: {coin['market_cap_rank']}")
                    st.write(f"Price (BTC): {coin['price_btc']:.8f}")
                    st.markdown("---")
            else:
                st.info("No trending coins data available")
        
        # Performance metrics in sidebar
        with st.sidebar:
            st.subheader("⚡ Performance Metrics")
            if st.session_state.request_times:
                avg_time = np.mean(st.session_state.request_times)
                p95_time = np.percentile(st.session_state.request_times, 95)
                st.write(f"Avg Response Time: {avg_time:.2f}s")
                st.write(f"P95 Response Time: {p95_time:.2f}s")
                
                # Clear old metrics periodically
                if len(st.session_state.request_times) > 1000:
                    st.session_state.request_times = st.session_state.request_times[-100:]
        
        # Token Monitor
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Go to", ["Trading Dashboard", "Token Monitor"])
        
        if page == "Token Monitor":
            st.title("Token Monitor Dashboard")
            
            # Metrics Row
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                recent_tokens = db.get_recent_tokens(24)
                st.metric("New Tokens (24h)", len(recent_tokens))
            
            with col2:
                high_opp_tokens = db.get_high_opportunity_tokens()
                st.metric("High Opportunity Tokens", len(high_opp_tokens))
            
            with col3:
                recent_alerts = db.get_recent_alerts(24)
                st.metric("Recent Alerts", len(recent_alerts))
            
            with col4:
                avg_opp_score = sum(t['opportunity_score'] for t in high_opp_tokens) / len(high_opp_tokens) if high_opp_tokens else 0
                st.metric("Avg Opportunity Score", f"{avg_opp_score:.2f}")
            
            # Recent Tokens Table
            st.subheader("Recently Discovered Tokens")
            if recent_tokens:
                df_recent = pd.DataFrame(recent_tokens)
                df_recent['timestamp'] = pd.to_datetime(df_recent['timestamp'])
                df_recent = df_recent.sort_values('timestamp', ascending=False)
                
                st.dataframe(
                    df_recent[[
                        'timestamp', 'symbol', 'name', 'initial_price',
                        'initial_market_cap', 'chain', 'source'
                    ]].style.format({
                        'initial_price': '${:,.2f}',
                        'initial_market_cap': '${:,.0f}',
                        'timestamp': lambda x: x.strftime('%Y-%m-%d %H:%M:%S')
                    })
                )
            else:
                st.info("No new tokens discovered in the last 24 hours")
            
            # High Opportunity Tokens
            st.subheader("High Opportunity Tokens")
            if high_opp_tokens:
                df_high_opp = pd.DataFrame(high_opp_tokens)
                df_high_opp['timestamp'] = pd.to_datetime(df_high_opp['timestamp'])
                df_high_opp = df_high_opp.sort_values('opportunity_score', ascending=False)
                
                # Opportunity Score Chart
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df_high_opp['symbol'],
                    y=df_high_opp['opportunity_score'],
                    name='Opportunity Score',
                    marker_color='rgb(55, 83, 109)'
                ))
                fig.update_layout(
                    title='Token Opportunity Scores',
                    xaxis_title='Token Symbol',
                    yaxis_title='Score',
                    yaxis_range=[0, 1]
                )
                st.plotly_chart(fig)
                
                # Detailed Metrics Table
                st.dataframe(
                    df_high_opp[[
                        'symbol', 'opportunity_score', 'initial_momentum',
                        'social_score', 'risk_score', 'timestamp'
                    ]].style.format({
                        'opportunity_score': '{:.2f}',
                        'initial_momentum': '{:.2f}',
                        'social_score': '{:.2f}',
                        'risk_score': '{:.2f}',
                        'timestamp': lambda x: x.strftime('%Y-%m-%d %H:%M:%S')
                    })
                )
            else:
                st.info("No high opportunity tokens found")
            
            # Recent Alerts
            st.subheader("Recent Alerts")
            if recent_alerts:
                df_alerts = pd.DataFrame(recent_alerts)
                df_alerts['timestamp'] = pd.to_datetime(df_alerts['timestamp'])
                df_alerts = df_alerts.sort_values('timestamp', ascending=False)
                
                for _, alert in df_alerts.iterrows():
                    with st.expander(f"{alert['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - {alert['symbol']}"):
                        cols = st.columns(4)
                        cols[0].metric("Opportunity Score", f"{alert['opportunity_score']:.2f}")
                        cols[1].metric("Momentum Score", f"{alert['momentum_score']:.2f}")
                        cols[2].metric("Social Score", f"{alert['social_score']:.2f}")
                        cols[3].metric("Risk Score", f"{alert['risk_score']:.2f}")
                        st.info(alert['alert_message'])
            else:
                st.info("No recent alerts")
    
    except Exception as e:
        logger.error(f"Main function error: {str(e)}")
        st.error("An unexpected error occurred. Please try refreshing the page.")

if __name__ == "__main__":
    main()
