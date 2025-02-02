"""Main script to run the Solana trading bot."""

import asyncio
import logging
from bot.trading_bot import TradingBot, TradingConfig
from bot.wallet.phantom_integration import PhantomWalletManager
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to run the trading bot."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Initialize wallet
        wallet = PhantomWalletManager()
        success, message = wallet.connect()
        if not success:
            logger.error(f"Failed to connect wallet: {message}")
            return
        
        # Create trading configuration
        config = TradingConfig(
            position_size_sol=float(os.getenv('POSITION_SIZE_SOL', '0.1')),
            stop_loss_percent=float(os.getenv('STOP_LOSS_PERCENT', '5')) / 100,
            take_profit_percent=float(os.getenv('TAKE_PROFIT_PERCENT', '10')) / 100,
            max_slippage_percent=float(os.getenv('MAX_SLIPPAGE_PERCENT', '1')) / 100,
            network=os.getenv('SOLANA_NETWORK', 'mainnet-beta'),
            max_positions=int(os.getenv('MAX_POSITIONS', '5')),
            max_trades_per_day=int(os.getenv('MAX_TRADES_PER_DAY', '10')),
            order_timeout=int(os.getenv('ORDER_TIMEOUT', '30'))
        )
        
        # Initialize trading bot
        bot = TradingBot(wallet=wallet, config=config)
        
        # Start trading
        await bot.start_trading()
        
        # Keep the script running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Stopping bot due to keyboard interrupt...")
        if 'bot' in locals():
            await bot.stop_trading()
    except Exception as e:
        logger.error(f"Error running trading bot: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
