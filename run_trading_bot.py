"""Main script to run the trading bot."""

import asyncio
import logging
import os
import sys
import yaml
from pathlib import Path
from bot.trading_bot import TradingBot
from bot.wallet.phantom_integration import PhantomWalletManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('trading_bot.log')
    ]
)

logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from YAML file."""
    try:
        config_path = Path('secure_config') / 'config.yaml'
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found at {config_path}")
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Validate required config sections
        required_sections = ['api_keys', 'network', 'wallet', 'trading']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required config section: {section}")
                
        logger.info("Configuration loaded successfully")
        return config
        
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        raise

async def main():
    """Main function to run the trading bot."""
    try:
        # Load configuration
        logger.info("Starting trading bot...")
        config = load_config()
        
        # Initialize wallet
        logger.info("Initializing wallet...")
        wallet = PhantomWalletManager(config)
        success, message = wallet.connect()
        if not success:
            logger.error(f"Failed to connect wallet: {message}")
            return
            
        # Initialize and start trading bot
        logger.info("Initializing trading bot...")
        bot = TradingBot(wallet=wallet, config=config)
        
        try:
            # Start trading
            logger.info("Starting trading operations...")
            await bot.start_trading()
            
        except KeyboardInterrupt:
            logger.info("Received shutdown signal, stopping bot gracefully...")
            await bot.stop_trading()
            
        except Exception as e:
            logger.error(f"Error during trading: {str(e)}", exc_info=True)
            await bot.stop_trading()
            raise
            
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1)
