import os
import sys
import logging
from decimal import Decimal
import time
import yaml

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from bot.memescope_sniper import MemescopeSniper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('memescope_sniper.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Initialize sniper bot
        sniper = MemescopeSniper(headless=False)  # Set to True for headless mode
        
        # Navigate to memescope
        if not sniper.navigate_to_memescope():
            logger.error("Failed to navigate to memescope")
            return
            
        while True:
            try:
                # Scan for tokens
                logger.info("Scanning for tokens...")
                tokens = sniper.scan_tokens()
                logger.info(f"Found {len(tokens)} tokens")
                
                # Analyze opportunities
                opportunities = sniper.analyze_migration_opportunities(tokens)
                
                if opportunities:
                    logger.info("\nTop opportunities found:")
                    for opp in opportunities[:3]:  # Show top 3
                        logger.info(f"\nToken: {opp['symbol']}")
                        logger.info(f"Score: {opp['score']}")
                        logger.info(f"Price: ${opp['price']}")
                        logger.info(f"Market Cap: ${opp['market_cap']}")
                        logger.info(f"Volume: ${opp['volume']}")
                        logger.info(f"Holders: {opp['holders']}")
                        logger.info(f"Reasons: {', '.join(opp['reasons'])}")
                        
                        # Uncomment to enable auto-trading
                        """
                        if opp['score'] >= 7:  # High-confidence opportunity
                            logger.info(f"\nAttempting to trade {opp['symbol']}...")
                            amount = Decimal('0.1')  # Test with 0.1 SOL
                            if sniper.execute_trade(opp, amount):
                                logger.info(f"Successfully traded {amount} SOL for {opp['symbol']}")
                            else:
                                logger.error(f"Failed to trade {opp['symbol']}")
                        """
                        
                else:
                    logger.info("No significant opportunities found")
                    
                # Wait before next scan
                logger.info("\nWaiting 30 seconds before next scan...")
                time.sleep(30)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(10)  # Wait before retrying
                
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
    finally:
        if 'sniper' in locals():
            sniper.cleanup()

if __name__ == "__main__":
    main()
