import streamlit as st
import aiohttp
import asyncio
import pandas as pd
from datetime import datetime, timedelta
import logging
from contextlib import asynccontextmanager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketDataFetcher:
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    @asynccontextmanager
    async def get_session(self):
        """Get or create an aiohttp session"""
        try:
            if not self.session or self.session.closed:
                self.session = aiohttp.ClientSession(headers=self.headers)
            yield self.session
        except Exception as e:
            logger.error(f"Session error: {str(e)}")
            if self.session and not self.session.closed:
                await self.session.close()
            self.session = None
            raise
    
    async def stop(self):
        """Cleanup resources"""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
                self.session = None
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    async def get_token_price(self, token_id="bitcoin"):
        """Get basic price data from CoinGecko"""
        try:
            async with self.get_session() as session:
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd&include_24hr_change=true"
                async with session.get(url) as response:
                    if response.status == 429:  # Rate limit
                        st.error("Rate limit hit. Please wait a minute and try again.")
                        return None
                    response.raise_for_status()
                    data = await response.json()
                    return data.get(token_id, {})
        except aiohttp.ClientError as e:
            logger.error(f"Network error: {str(e)}")
            st.error("Network error occurred. Please check your connection.")
            return None
        except Exception as e:
            logger.error(f"Error fetching price: {str(e)}")
            st.error("An unexpected error occurred.")
            return None

    async def get_trending_tokens(self):
        """Get trending tokens from CoinGecko"""
        try:
            async with self.get_session() as session:
                url = "https://api.coingecko.com/api/v3/search/trending"
                async with session.get(url) as response:
                    if response.status == 429:  # Rate limit
                        st.error("Rate limit hit. Please wait a minute and try again.")
                        return []
                    response.raise_for_status()
                    data = await response.json()
                    return [
                        {
                            "name": coin["item"]["name"],
                            "symbol": coin["item"]["symbol"].upper(),
                            "price_btc": coin["item"]["price_btc"]
                        }
                        for coin in data.get("coins", [])[:5]
                    ]
        except aiohttp.ClientError as e:
            logger.error(f"Network error: {str(e)}")
            st.error("Network error occurred. Please check your connection.")
            return []
        except Exception as e:
            logger.error(f"Error fetching trending tokens: {str(e)}")
            st.error("An unexpected error occurred.")
            return []

async def main():
    st.set_page_config(
        page_title="CryptoBot Test",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("CryptoBot Market Data Test")
    
    # Initialize fetcher
    fetcher = MarketDataFetcher()
    try:
        # Get Bitcoin price
        btc_data = await fetcher.get_token_price()
        if btc_data:
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "Bitcoin Price",
                    f"${btc_data.get('usd', 0):,.2f}",
                    f"{btc_data.get('usd_24h_change', 0):.2f}%"
                )
        
        # Get trending tokens
        trending = await fetcher.get_trending_tokens()
        if trending:
            st.subheader("Trending Tokens")
            df = pd.DataFrame(trending)
            st.dataframe(df)
            
        # Add refresh button
        if st.button("Refresh Data"):
            st.experimental_rerun()
            
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error("An error occurred while fetching data.")
    finally:
        # Cleanup
        await fetcher.stop()

if __name__ == "__main__":
    asyncio.run(main())
