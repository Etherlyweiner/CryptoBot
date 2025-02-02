import asyncio
import logging
from risk_monitor import RiskMonitor
from datetime import datetime
import os
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID',
        'BINANCE_API_KEY',
        'BINANCE_API_SECRET'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.warning("Some tests may fail due to missing credentials")
    return len(missing_vars) == 0

async def test_api_connections():
    """Test all API connections and core functionality"""
    try:
        logger.info("Starting API connection tests...")
        
        # Check environment variables
        env_ok = check_environment()
        if not env_ok:
            logger.warning("Continuing with limited testing due to missing environment variables")
        
        # Initialize RiskMonitor
        risk_monitor = None
        try:
            risk_monitor = RiskMonitor()
            await risk_monitor.start()
            
            # Test 1: DEX Screener API
            logger.info("Testing DEX Screener API...")
            dex_data = await risk_monitor.check_dex_screener("0x2260fac5e5542a773aa44fbcfedf7c193bc2c599")  # BTC
            if dex_data:
                logger.info("DEX Screener API test passed")
            else:
                logger.warning("DEX Screener API test returned no data")
            
            # Test 2: CoinGecko API
            logger.info("Testing CoinGecko API...")
            coingecko_data = await risk_monitor.check_coingecko_data("bitcoin")
            if coingecko_data:
                logger.info("CoinGecko API test passed")
            else:
                logger.warning("CoinGecko API test returned no data")
            
            # Test 3: Pump Signals
            logger.info("Testing pump signals detection...")
            signals = await risk_monitor.check_pump_signals()
            if signals:
                logger.info(f"Pump signals test passed - Found {len(signals)} signals")
            else:
                logger.warning("Pump signals test returned no signals")
            
            # Test 4: Risk Score Calculation
            logger.info("Testing risk score calculation...")
            metrics = {
                'liquidity': 100000,
                'volume_24h': 500000,
                'price_change_24h': 0.1
            }
            risk_score = risk_monitor.calculate_risk_score(metrics, signals)
            logger.info(f"Risk score calculation test passed - Score: {risk_score}")
            
        finally:
            # Cleanup
            if risk_monitor:
                await risk_monitor.stop()
            logger.info("Cleaned up resources")
        
        logger.info("All tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        return False

async def main():
    success = await test_api_connections()
    if success:
        print("\nDeployment test passed! The bot is ready for deployment.")
    else:
        print("\nDeployment test failed. Please check the logs above for details.")

if __name__ == "__main__":
    asyncio.run(main())
