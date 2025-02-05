"""Script to start both the trading bot and web server."""

import asyncio
import logging
import os
import signal
import sys
from subprocess import Popen

import yaml
from bot.trading_bot import TradingBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point."""
    try:
        # Load config
        with open('secure_config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            
        # Start web server
        server_process = Popen(['node', 'server.js'])
        logger.info("Web server started")
        
        # Initialize and start trading bot
        bot = TradingBot(config)
        await bot.start()
        
        # Handle shutdown
        def signal_handler(signum, frame):
            logger.info("Shutting down...")
            server_process.terminate()
            asyncio.create_task(bot.stop())
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.exception(f"Error in main: {str(e)}")
        if 'server_process' in locals():
            server_process.terminate()
        sys.exit(1)
        
if __name__ == '__main__':
    asyncio.run(main())
