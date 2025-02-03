"""
Test Phantom Wallet Integration
"""

import asyncio
import os
from cryptobot.trading.phantom import PhantomWallet
from cryptobot.trading.engine import TradingEngine
from cryptobot.monitoring.logger import BotLogger

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

async def test_trading_engine():
    """Test trading engine with Phantom Wallet."""
    logger = BotLogger()
    engine = TradingEngine()
    
    logger.info("Testing Trading Engine integration...")
    
    try:
        # Initialize trading engine
        await engine.initialize()
        logger.info("✅ Trading Engine initialized successfully")
        
        # Get current portfolio value
        value = engine.get_portfolio_value()
        logger.info(f"Current portfolio value: {value:.4f} SOL")
        
        # Get current positions
        positions = engine.get_positions()
        if positions:
            logger.info("Current positions:")
            for pos in positions:
                logger.info(f"  {pos['token']}: {pos['balance']} @ ${pos['price']:.4f}")
        else:
            logger.info("No active positions")
        
        # Test market data fetching
        logger.info("Fetching market data...")
        market_data = await engine.get_market_data()
        if market_data:
            logger.info("Market data received:")
            for token, price in market_data.items():
                logger.info(f"  {token}: ${price:.4f}")
        else:
            logger.warning("Failed to fetch market data")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Trading Engine test failed: {str(e)}")
        return False

async def main():
    """Run all integration tests."""
    logger = BotLogger()
    logger.info("Starting Phantom Wallet integration tests...")
    
    # Test Phantom connection
    if not await test_phantom_connection():
        logger.error("Phantom Wallet connection test failed")
        return
    
    # Test trading engine
    if not await test_trading_engine():
        logger.error("Trading Engine test failed")
        return
    
    logger.info("✅ All integration tests completed successfully")

if __name__ == "__main__":
    asyncio.run(main())
