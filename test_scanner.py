import asyncio
import json
import logging
from cryptobot.token_scanner import TokenScanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    try:
        # Load config
        with open('config/config.json', 'r') as f:
            config = json.load(f)
        
        logger.info("Testing token scanner...")
        scanner = TokenScanner(config)
        
        # Scan for new tokens
        logger.info("\nScanning for new tokens...")
        new_tokens = await scanner.scan_new_tokens()
        
        logger.info(f"\nFound {len(new_tokens)} new tokens")
        if new_tokens:
            logger.info("\nFirst 5 tokens:")
            for token in new_tokens[:5]:
                logger.info(json.dumps(token, indent=2))
                
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
