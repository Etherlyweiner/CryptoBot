import streamlit as st
import pandas as pd
from typing import Dict, List
import ccxt
from datetime import datetime, timedelta

@st.cache_resource
def get_exchange():
    """Initialize and cache the exchange connection."""
    return ccxt.binance()

@st.cache_data(ttl="5m")  # Cache for 5 minutes
def fetch_current_prices(symbols: List[str]) -> Dict[str, float]:
    """Fetch current prices for multiple symbols."""
    exchange = get_exchange()
    prices = {}
    for symbol in symbols:
        try:
            ticker = exchange.fetch_ticker(symbol)
            prices[symbol] = ticker['last']
        except Exception as e:
            st.warning(f"Error fetching price for {symbol}: {str(e)}")
            prices[symbol] = None
    return prices

@st.cache_data(ttl="1h")  # Cache for 1 hour
def fetch_historical_data(symbol: str, timeframe: str = '1h', limit: int = 168) -> pd.DataFrame:
    """Fetch historical OHLCV data with caching."""
    try:
        exchange = get_exchange()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        st.error(f"Error fetching historical data: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl="15m")  # Cache for 15 minutes
def get_market_overview() -> Dict:
    """Get market overview data."""
    exchange = get_exchange()
    try:
        tickers = exchange.fetch_tickers()
        volumes = {k: v['quoteVolume'] for k, v in tickers.items() if v['quoteVolume']}
        top_volume = dict(sorted(volumes.items(), key=lambda x: x[1], reverse=True)[:10])
        
        return {
            'total_markets': len(tickers),
            'top_volume_pairs': top_volume
        }
    except Exception as e:
        st.error(f"Error fetching market overview: {str(e)}")
        return {}
