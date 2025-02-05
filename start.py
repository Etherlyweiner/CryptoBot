"""Script to start both the trading bot and web server."""

import asyncio
import logging
import os
import signal
import sys
from subprocess import Popen
import time

import yaml
import redis
from bot.trading_bot import TradingBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/startup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def wait_for_redis(max_retries=5, retry_delay=2):
    """Wait for Redis to be available."""
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    for attempt in range(max_retries):
        try:
            if redis_client.ping():
                logger.info("Redis connection successful")
                return True
        except redis.ConnectionError:
            if attempt < max_retries - 1:
                logger.warning(f"Redis not available, retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Failed to connect to Redis")
                return False
    return False

async def wait_for_server(port=8000, max_retries=10, retry_delay=1):
    """Wait for the web server to start."""
    import socket
    for attempt in range(max_retries):
        try:
            with socket.create_connection(('localhost', port), timeout=1):
                logger.info(f"Server is running on port {port}")
                return True
        except (socket.timeout, ConnectionRefusedError):
            if attempt < max_retries - 1:
                logger.warning(f"Server not ready, retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Server failed to start on port {port}")
                return False
    return False

async def main():
    """Main entry point."""
    try:
        # Wait for Redis
        if not await wait_for_redis():
            logger.error("Redis is not available. Please start Redis first.")
            return

        # Load config
        with open('secure_config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            
        # Start web server using full path to node
        node_path = r"C:\Program Files\nodejs\node.exe"
        server_js = os.path.join(os.path.dirname(__file__), 'server.js')
        server_process = Popen([node_path, server_js])
        logger.info("Web server process started")
        
        # Wait for server to be ready
        if not await wait_for_server():
            logger.error("Web server failed to start")
            server_process.terminate()
            return
            
        # Initialize and start trading bot
        bot = TradingBot(config)
        await bot.start()
        logger.info("Trading bot started successfully")
        
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
        logger.exception(f"Error starting trading bot: {str(e)}")
        if 'server_process' in locals():
            server_process.terminate()
        sys.exit(1)
        
if __name__ == '__main__':
    asyncio.run(main())
