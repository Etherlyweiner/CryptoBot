import os
import sys
import asyncio
import yaml
import logging
import psutil
from bot.photon_trader import PhotonTrader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_browser_ready():
    """Check if Edge is running with remote debugging."""
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if proc.info['name'] == 'msedge.exe':
                cmdline = proc.info['cmdline']
                if cmdline and '--remote-debugging-port=9222' in ' '.join(cmdline):
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

async def main():
    try:
        # Check if browser is ready
        if not check_browser_ready():
            logger.error("Edge browser not running with remote debugging")
            logger.info("Please start the browser first:")
            logger.info("Run: python start_browser.py")
            return
            
        logger.info("Loading configuration...")
        with open("config/config.yaml", "r") as f:
            config = yaml.safe_load(f)
            
        logger.info("Creating trader instance...")
        trader = PhotonTrader(config)
        
        logger.info("Connecting to existing browser session...")
        if not await trader.initialize(manual_auth=True):
            logger.error("Failed to initialize trader. Please ensure you're logged in to Photon DEX")
            await trader.cleanup()
            return
            
        logger.info("Starting opportunity scan...")
        opportunities = await trader.scan_for_opportunities()
        
        if opportunities:
            logger.info(f"Found {len(opportunities)} opportunities:")
            for token, score, reason in opportunities:
                logger.info(f"Token: {token.symbol}")
                logger.info(f"Score: {score}")
                logger.info(f"Reason: {reason}")
                logger.info("-" * 50)
        else:
            logger.info("No opportunities found at this time")
            
        await trader.cleanup()
        logger.info("Bot resources cleaned up")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        if 'trader' in locals():
            await trader.cleanup()
            
if __name__ == "__main__":
    asyncio.run(main())
