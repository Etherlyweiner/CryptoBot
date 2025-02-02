import asyncio
import os
import logging
from bot import TradingBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CryptoBot')

# Set test environment variables
os.environ['PHANTOM_PUBLIC_KEY'] = 'DxPv2QMA5cWR5Xj6N3qwW7BQEqWQCgHGk7JqhwfKKgRY'  # Test public key
os.environ['NETWORK'] = 'devnet'  # Use devnet for testing
os.environ['RPC_URL'] = 'https://api.devnet.solana.com'

async def main():
    bot = None
    try:
        logger.info("Initializing trading bot...")
        bot = TradingBot()
        
        logger.info("Starting bot...")
        await bot.start()
        
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}", exc_info=True)
    finally:
        if bot:
            logger.info("Cleaning up...")
            await bot.wallet.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
