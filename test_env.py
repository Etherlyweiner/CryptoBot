import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get current working directory
cwd = Path(__file__).parent.absolute()
logger.debug(f"Current working directory: {cwd}")

# Find and load .env file
env_path = cwd / '.env'
logger.debug(f"Looking for .env at: {env_path}")

if not env_path.exists():
    logger.error(f".env file not found at {env_path}")
else:
    logger.debug("Loading .env file...")
    load_dotenv(dotenv_path=env_path, override=True)
    
    api_key = os.environ.get('BINANCE_API_KEY')
    api_secret = os.environ.get('BINANCE_API_SECRET')
    
    logger.debug(f"API Key found: {'Yes' if api_key else 'No'}")
    if api_key:
        logger.debug(f"API Key length: {len(api_key)}")
        logger.debug(f"API Key prefix: {api_key[:4]}")
    
    logger.debug(f"API Secret found: {'Yes' if api_secret else 'No'}")
    if api_secret:
        logger.debug(f"API Secret length: {len(api_secret)}")
        
    # Print all environment variables
    logger.debug("\nAll environment variables:")
    for key, value in os.environ.items():
        if 'BINANCE' in key:
            logger.debug(f"{key}: {'*' * len(value)}")

if __name__ == '__main__':
    test_env()
