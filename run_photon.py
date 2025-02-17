#!/usr/bin/env python3
"""
Direct runner for Photon DEX Trading Bot
Focused on meme token trading with stealth and anti-detection
"""

import logging
import keyboard
import time
from photon_trader import PhotonTrader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('photon_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('PhotonTrader')

def test_interface():
    """Test the trading interface functionality."""
    try:
        logger.info("Testing interface functionality...")
        trader = PhotonTrader()
        
        try:
            logger.info("Starting interface test...")
            
            # Test navigation
            logger.info("Navigating to memescope section...")
            if not trader.navigate_to_memescope():
                raise Exception("Failed to navigate to memescope")
            
            # Test token scanning
            logger.info("Scanning for new tokens...")
            tokens = trader.scan_tokens()
            if not tokens:
                raise Exception("Failed to scan tokens")
                
            # Test successful
            logger.info("Interface test completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Interface test failed. Please check the logs.")
            return False
            
        finally:
            # Clean up but preserve browser session
            trader.cleanup()
            
    except Exception as e:
        logger.error(f"Failed to initialize trader: {str(e)}")
        return False

def main():
    """Main entry point."""
    try:
        logger.info("Initializing Photon DEX Trading Bot...")
        
        # Test interface functionality
        if not test_interface():
            logger.error("Interface test failed, exiting...")
            return
            
        # Continue with main trading loop if test passes
        trader = PhotonTrader(config_path='config/config.yaml')
        try:
            while True:
                # Ensure browser is still responsive
                if trader.ensure_browser_alive():
                    logger.info("Browser restarted successfully")
                
                # Main trading logic here
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            trader.cleanup()
            
    except Exception as e:
        logger.error(f"Bot execution failed: {str(e)}")
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    main()
