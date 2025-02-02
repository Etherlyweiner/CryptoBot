"""
Main entry point for CryptoBot with improved components.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from bot.server import run_server
from bot.trade_database import TradeDatabaseManager
from bot.cache_manager import CacheManager
from bot.trade_processor import TradeProcessor
import ssl
import prometheus_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cryptobot.log')
    ]
)
logger = logging.getLogger(__name__)

def setup_ssl():
    """Setup SSL certificates if needed."""
    ssl_cert = os.getenv('SSL_CERT_PATH')
    ssl_key = os.getenv('SSL_KEY_PATH')
    
    if ssl_cert and ssl_key:
        if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(ssl_cert, ssl_key)
            return ssl_context
    return None

def setup_metrics():
    """Setup Prometheus metrics."""
    metrics_port = int(os.getenv('METRICS_PORT', '9090'))
    prometheus_client.start_http_server(metrics_port)
    logger.info(f"Metrics server started on port {metrics_port}")

async def main():
    """Main entry point with async support."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Setup components
        setup_metrics()
        ssl_context = setup_ssl()
        
        # Initialize services
        trade_processor = TradeProcessor(
            redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379')
        )
        
        # Start trade processor
        asyncio.create_task(trade_processor.start_processing())
        
        # Get server configuration
        host = os.getenv('SERVER_HOST', 'localhost')
        port = int(os.getenv('SERVER_PORT', '8080'))
        
        # Run server
        await run_server(
            hostname=host,
            port=port,
            metrics_port=int(os.getenv('METRICS_PORT', '9090'))
        )
        
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        await trade_processor.stop()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
