import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_session():
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

def main():
    st.set_page_config(
        page_title="Minimal Test",
        page_icon="🔍",
        layout="centered"
    )

    st.title("Minimal CryptoBot Test")
    st.write("Testing basic functionality")

    session = create_session()
    try:
        # Simple API test
        response = session.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        price = data.get("bitcoin", {}).get("usd", 0)
        st.success(f"Bitcoin Price: ${price:,.2f}")
            
    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        st.error("Request timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        st.error("Failed to fetch price data. Please check your connection.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        st.error("An unexpected error occurred.")
    finally:
        session.close()

    # Simple interaction test
    if st.button("Refresh"):
        st.experimental_rerun()

if __name__ == "__main__":
    main()
