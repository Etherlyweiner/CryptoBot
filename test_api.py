import logging
import ccxt
from config import Config

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_api_connection():
    """Test Binance.US API connection and credentials"""
    try:
        # Load config
        config = Config()
        logger.info("Configuration loaded successfully")
        
        # Initialize exchange
        exchange = ccxt.binanceus({
            'apiKey': config.BINANCE_API_KEY,
            'secret': config.BINANCE_API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
                'recvWindow': 10000
            }
        })
        logger.info("Exchange initialized")
        
        # Test public API
        logger.debug("Testing public API...")
        markets = exchange.load_markets()
        logger.info(f"Successfully loaded {len(markets)} markets")
        
        # Test private API
        logger.debug("Testing private API...")
        balance = exchange.fetch_balance()
        if balance:
            logger.info("Successfully fetched balance")
            for currency, amount in balance['total'].items():
                if float(amount) > 0:
                    logger.info(f"{currency}: {amount}")
        
        # Test specific symbols
        test_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        for symbol in test_symbols:
            logger.debug(f"Testing ticker for {symbol}...")
            ticker = exchange.fetch_ticker(symbol)
            logger.info(f"{symbol} last price: {ticker['last']}")
        
        logger.info("All API tests passed successfully!")
        return True
        
    except ccxt.AuthenticationError as e:
        logger.error("Authentication failed. Please check your API credentials.", exc_info=True)
        return False
    except ccxt.NetworkError as e:
        logger.error("Network error occurred.", exc_info=True)
        return False
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {str(e)}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return False

if __name__ == '__main__':
    test_api_connection()
