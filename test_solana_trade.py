"""Test Solana memecoin trading bot."""

import asyncio
import logging
from decimal import Decimal
import os
from dotenv import load_dotenv

from exchanges.solana import SolanaExchange
from exchanges.jupiter import JupiterDEX
from strategies.memecoin_strategy import MemeStrategy, StrategyConfig
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
        # Initialize exchange and DEX
        exchange = SolanaExchange({
            'rpc_url': os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        })
        
        dex = JupiterDEX({
            'rpc_url': os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        })
        
        # Connect to Phantom wallet
        await exchange.connect()
        
        # Configure strategy
        config = StrategyConfig(
            min_liquidity=Decimal('1000'),  # Minimum SOL liquidity
            max_slippage_bps=100,  # 1% max slippage
            min_confidence=0.7,  # 70% confidence required for trades
            position_size=Decimal('0.1'),  # 0.1 SOL per trade
            stop_loss_pct=Decimal('0.05'),  # 5% stop loss
            take_profit_pct=Decimal('0.2'),  # 20% take profit
            cooldown_minutes=60  # 1 hour cooldown between trades
        )
        
        # Initialize strategy
        strategy = MemeStrategy(exchange, dex, config)
        
        # Start system health monitoring
        health_task = asyncio.create_task(
            health_checker.monitor_health()
        )
        
        # Run strategy
        print("Starting Solana memecoin trading bot...")
        await strategy.run()
        
    except KeyboardInterrupt:
        print("\nStopping trading bot...")
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        # Clean up
        await exchange.close()
        await dex.close()
        health_task.cancel()
        
if __name__ == '__main__':
    asyncio.run(main())
