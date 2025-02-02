"""
Start monitoring script for CryptoBot
"""

import asyncio
import logging
import platform
from website_monitor import WebsiteMonitor
from market_monitor import MarketMonitor
from database import Database
from logging_config import setup_logging

async def main():
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize database
        db = Database()
        
        # Initialize monitors
        website_monitor = WebsiteMonitor(db)
        market_monitor = MarketMonitor(db)
        
        # Start monitoring tasks
        logger.info("Starting monitors...")
        monitoring_tasks = [
            website_monitor.start_monitoring(),
            market_monitor.run_monitoring_loop()
        ]
        
        # Run all monitoring tasks concurrently
        await asyncio.gather(*monitoring_tasks)
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    finally:
        await website_monitor.cleanup()
        await market_monitor.close_session()
        db.cleanup()

if __name__ == "__main__":
    if platform.system() == 'Windows':
        # Use ProactorEventLoop on Windows
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())
