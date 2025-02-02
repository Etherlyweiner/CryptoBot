"""
Test Binance.US API connection
"""
import ccxt
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ExchangeTest')

def test_exchange():
    try:
        # Load environment variables
        load_dotenv()
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        
        if not api_key or not api_secret:
            logger.error("API credentials not found in .env file")
            return False
            
        logger.info("Initializing Binance.US exchange...")
        
        # Initialize exchange with Binance.US
        exchange = ccxt.binanceus({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 60000,
                'createMarketBuyOrderRequiresPrice': False
            },
            'urls': {
                'api': {
                    'public': 'https://api.binance.us/api/v3',
                    'private': 'https://api.binance.us/api/v3',
                    'web': 'https://www.binance.us'
                }
            }
        })
        
        # Enable debugging
        exchange.verbose = True
        
        # Test connection
        logger.info("Testing connection...")
        exchange.load_markets()
        balance = exchange.fetch_balance()
        
        if balance and 'total' in balance:
            logger.info("Successfully connected to Binance.US")
            logger.info("Available markets: %s", len(exchange.markets))
            
            # Test fetch OHLCV
            symbol = 'BTC/USD'
            if symbol in exchange.markets:
                logger.info(f"Fetching OHLCV data for {symbol}...")
                ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=5)
                if ohlcv:
                    logger.info(f"Successfully fetched OHLCV data: {len(ohlcv)} candles")
            
            return True
            
        logger.error("Failed to get balance")
        return False
        
    except ccxt.AuthenticationError as e:
        logger.error("Authentication failed: %s", str(e))
        return False
    except ccxt.NetworkError as e:
        logger.error("Network error: %s", str(e))
        return False
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return False

if __name__ == "__main__":
    test_exchange()
