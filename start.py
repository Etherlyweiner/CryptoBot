"""CryptoBot - Autonomous Trading System."""

import asyncio
import logging
import os
import signal
import sys
from subprocess import Popen
import time
import traceback

import yaml
import redis
from bot.trading_bot import CryptoBot

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cryptobot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('CryptoBot.Startup')

async def wait_for_redis(max_retries=5, retry_delay=2):
    """Wait for Redis to be available."""
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    for attempt in range(max_retries):
        try:
            if redis_client.ping():
                logger.info("Redis connection successful")
                return True
        except redis.ConnectionError as e:
            if attempt < max_retries - 1:
                logger.warning(f"Redis not available (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay} seconds... Error: {str(e)}")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to Redis after {max_retries} attempts. Error: {str(e)}")
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
                logger.warning(f"Server not ready (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Server failed to start after {max_retries} attempts")
                return False
    return False

async def main():
    """Main entry point."""
    try:
        logger.info("Starting CryptoBot system...")
        
        # Wait for Redis
        if not await wait_for_redis():
            logger.error("Redis is not available. Please start Redis first.")
            return

        # Load config
        try:
            with open('config/config.yaml', 'r') as f:
                config = yaml.safe_load(f)
                logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            return
            
        # Start web server
        try:
            node_path = r"C:\Program Files\nodejs\node.exe"
            server_js = os.path.join(os.path.dirname(__file__), 'server.js')
            server_process = Popen([node_path, server_js], 
                                stdout=open('logs/server.log', 'a'),
                                stderr=open('logs/server.error.log', 'a'))
            logger.info("Web server process started")
        except Exception as e:
            logger.error(f"Failed to start web server: {str(e)}\n{traceback.format_exc()}")
            return
        
        # Wait for server to be ready
        if not await wait_for_server():
            logger.error("Web server failed to start")
            server_process.terminate()
            return
            
        # Initialize and start trading bot
        try:
            bot = CryptoBot(config)
            await bot.start()
            logger.info("CryptoBot started successfully")
        except Exception as e:
            logger.error(f"Failed to start CryptoBot: {str(e)}\n{traceback.format_exc()}")
            server_process.terminate()
            return
        
        # Handle shutdown
        def signal_handler(signum, frame):
            logger.info("Shutting down CryptoBot...")
            server_process.terminate()
            asyncio.create_task(bot.stop())
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Unexpected error in main: {str(e)}\n{traceback.format_exc()}")
        if 'server_process' in locals():
            server_process.terminate()
        sys.exit(1)
        
if __name__ == '__main__':
    asyncio.run(main())
