import asyncio
import logging
from pathlib import Path
from src.cryptobot.main import CryptoBot
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cryptobot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("CryptoBot")

async def main():
    try:
        # Initialize bot
        bot = CryptoBot()
        
        # Start bot
        logger.info("Starting CryptoBot...")
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Shutting down bot...")
        await bot.stop()
    except Exception as e:
        logger.error(f"Bot error: {str(e)}")
        logger.exception("Full error trace:")
    finally:
        # Ensure cleanup
        await bot.cleanup()

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
