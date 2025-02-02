import streamlit as st
import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CoinGeckoAPI:
    def __init__(self):
        self.session = self._create_session()
        self.base_url = "https://api.coingecko.com/api/v3"
    
    def _create_session(self):
        """Create a requests session with retries and timeouts"""
        session = requests.Session()
        
        # Configure retries
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        # Configure the adapter with retries
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    def get_bitcoin_price(self):
        """Get basic Bitcoin price data"""
        try:
            url = f"{self.base_url}/simple/price"
            params = {
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_24hr_change": "true"
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get("bitcoin", {})
            
        except requests.exceptions.Timeout:
            logger.error("Request timed out")
            st.error("Request timed out. Please try again.")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            st.error("Failed to fetch Bitcoin price. Please check your connection.")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            st.error("An unexpected error occurred.")
            return None

    def get_trending_coins(self):
        """Get trending coins"""
        try:
            url = f"{self.base_url}/search/trending"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return [
                {
                    "name": coin["item"]["name"],
                    "symbol": coin["item"]["symbol"].upper(),
                    "market_cap_rank": coin["item"].get("market_cap_rank", "N/A")
                }
                for coin in data.get("coins", [])[:5]
            ]
            
        except requests.exceptions.Timeout:
            logger.error("Request timed out")
            st.error("Request timed out. Please try again.")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            st.error("Failed to fetch trending coins. Please check your connection.")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            st.error("An unexpected error occurred.")
            return []
    
    def close(self):
        """Close the session"""
        try:
            if self.session:
                self.session.close()
        except Exception as e:
            logger.error(f"Error closing session: {str(e)}")

def main():
    # Page config
    st.set_page_config(
        page_title="CryptoBot Test",
        page_icon="📊",
        layout="wide"
    )

    # Title
    st.title("CryptoBot Test Dashboard")
    st.markdown("---")

    # Initialize API client
    api = CoinGeckoAPI()
    try:
        # Create columns
        col1, col2 = st.columns(2)

        # Column 1: Bitcoin Price
        with col1:
            st.subheader("Bitcoin Price")
            btc_data = api.get_bitcoin_price()
            
            if btc_data:
                price = btc_data.get("usd", 0)
                change = btc_data.get("usd_24h_change", 0)
                
                st.metric(
                    label="Current Price",
                    value=f"${price:,.2f}",
                    delta=f"{change:.2f}%" if change else None
                )
            else:
                st.warning("Unable to fetch Bitcoin price")

        # Column 2: Trending Coins
        with col2:
            st.subheader("Trending Coins")
            trending = api.get_trending_coins()
            
            if trending:
                df = pd.DataFrame(trending)
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("Unable to fetch trending coins")

        # Refresh button
        if st.button("Refresh Data"):
            st.experimental_rerun()

        # Version info in sidebar
        st.sidebar.info("Test Version 1.0")

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error("An error occurred while running the application.")
    finally:
        api.close()

if __name__ == "__main__":
    main()
