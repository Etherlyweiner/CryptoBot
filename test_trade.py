"""Test trading script."""

import asyncio
import logging
from decimal import Decimal
import os
from dotenv import load_dotenv

from exchanges.binance import BinanceExchange
from trading_bot import TradingBot, TradingConfig
from metrics_collector import metrics
from system_health import health_checker

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """Run trading test."""
    try:
        # Initialize exchange
        exchange = BinanceExchange({
            'api_key': os.getenv('BINANCE_API_KEY'),
            'api_secret': os.getenv('BINANCE_API_SECRET'),
            'testnet': True  # Use testnet for testing
        })
        
        # Configure trading parameters
        config = TradingConfig(
            symbol='BTC/USDT',
            base_currency='BTC',
            quote_currency='USDT',
            position_size=Decimal('0.1'),  # 10% of available balance
            max_positions=1,
            stop_loss_pct=Decimal('0.02'),  # 2%
            take_profit_pct=Decimal('0.05'),  # 5%
            max_slippage_pct=Decimal('0.001')  # 0.1%
        )
        
        # Initialize trading bot
        bot = TradingBot(exchange, config)
        
        # Start system health monitoring
        health_task = asyncio.create_task(
            health_checker.monitor_health()
        )
        
        # Run trading bot
        print("Starting trading bot...")
        await bot.run()
        
    except KeyboardInterrupt:
        print("\nStopping trading bot...")
        await bot.stop()
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        # Clean up
        await exchange.close()
        health_task.cancel()
        
if __name__ == '__main__':
    asyncio.run(main())
