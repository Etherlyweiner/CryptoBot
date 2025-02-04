"""
Test Phantom Wallet Integration
"""

import asyncio
import os
import sys
import pytest

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from cryptobot.trading.phantom import PhantomWallet
from cryptobot.trading.engine import TradingEngine
from cryptobot.monitoring.logger import BotLogger

@pytest.mark.asyncio
async def test_phantom_connection():
    """Test connection to Phantom Wallet."""
    logger = BotLogger()
    phantom = PhantomWallet()
    
    logger.info("Testing Phantom Wallet connection...")
    
    # Test initialization
    success = await phantom.initialize()
    if not success:
        logger.error("❌ Failed to initialize Phantom Wallet")
        return False
    
    logger.info("✅ Successfully connected to Phantom Wallet")
    
    # Get wallet balances
    logger.info("Fetching wallet balances...")
    balances = await phantom.get_memecoin_balances()
    
    if balances:
        logger.info("Current balances:")
        for token, amount in balances.items():
            logger.info(f"  {token}: {amount}")
    else:
        logger.warning("No memecoin balances found")
    
    # Get current prices
    logger.info("Fetching current prices...")
    prices = await phantom.get_memecoin_prices()
    
    if prices:
        logger.info("Current prices:")
        for token, price in prices.items():
            logger.info(f"  {token}: ${price:.4f}")
    else:
        logger.warning("Failed to fetch prices")
    
    return True

@pytest.mark.asyncio
async def test_trading_engine():
    """Test trading engine with Phantom Wallet."""
    logger = BotLogger()
    phantom = PhantomWallet()
    config = {
        'max_position_size': 1.0,
        'stop_loss': 0.05,
        'take_profit': 0.1,
        'trailing_stop': 0.02
    }
    engine = TradingEngine(config)
    engine.set_wallet(phantom)
    
    logger.info("Testing Trading Engine...")
    
    # Test engine initialization
    success = await engine.initialize()
    if not success:
        logger.error("❌ Failed to initialize Trading Engine")
        return False
    
    logger.info("✅ Successfully initialized Trading Engine")
    
    # Test order placement
    logger.info("Testing order placement...")
    order = await engine.place_test_order()
    
    if order:
        logger.info(f"✅ Successfully placed test order: {order}")
    else:
        logger.warning("Failed to place test order")
    
    # Test order cancellation
    if order:
        logger.info("Testing order cancellation...")
        cancelled = await engine.cancel_order(order['id'])
        
        if cancelled:
            logger.info("✅ Successfully cancelled test order")
        else:
            logger.warning("Failed to cancel test order")
    
    return True

async def main():
    """Run all integration tests."""
    logger = BotLogger()
    
    logger.info("Starting Phantom Wallet Integration Tests...")
    
    success = await test_phantom_connection()
    if not success:
        logger.error("❌ Phantom Wallet connection tests failed")
        return
    
    success = await test_trading_engine()
    if not success:
        logger.error("❌ Trading Engine tests failed")
        return
    
    logger.info("✅ All integration tests passed successfully")

if __name__ == "__main__":
    asyncio.run(main())
