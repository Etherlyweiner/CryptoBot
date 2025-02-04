"""Test script for BirdEye API integration"""
import asyncio
import json
import logging
from pathlib import Path
from src.cryptobot.sniper_bot import SniperBot
from src.cryptobot.token_scanner import TokenScanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_birdeye_api():
    """Test BirdEye API integration"""
    try:
        # Load config
        config_path = Path('config/config.json')
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found at {config_path}")
            
        with open(config_path) as f:
            config = json.load(f)
        
        # Verify BirdEye API key
        birdeye_config = config.get('birdeye', {})
        if not birdeye_config.get('api_key'):
            raise ValueError("BirdEye API key not found in config")
            
        logger.info("Starting BirdEye API test...")
        
        # Test known token first (SAMO)
        samo_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        logger.info(f"\nTesting token analysis with SAMO token ({samo_address})...")
        
        async with SniperBot(config) as sniper:
            analysis = await sniper._analyze_token(samo_address)
            logger.info("\nSAMO Token Analysis:")
            logger.info(json.dumps(analysis, indent=2))
        
        # Test token scanning
        logger.info("\nScanning for new tokens...")
        async with TokenScanner(config) as scanner:
            new_tokens = await scanner.scan_new_tokens()
            logger.info(f"\nFound {len(new_tokens)} new tokens")
            
            if new_tokens:
                first_token = new_tokens[0]
                logger.info("\nAnalyzing first new token...")
                async with SniperBot(config) as sniper:
                    analysis = await sniper._analyze_token(first_token['address'])
                    logger.info(f"\nToken Address: {first_token['address']}")
                    logger.info(json.dumps(analysis, indent=2))
            else:
                logger.warning("No new tokens found to analyze")

    except Exception as e:
        logger.error(f"Error in test script: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_birdeye_api())
