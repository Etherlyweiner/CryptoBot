"""
Test real-time trade recording functionality
"""

import asyncio
import sys
import platform
from bot import TradingBot
from database import Database
from datetime import datetime, timedelta
import logging
from logging_config import get_logger
import os

logger = get_logger('TestTradeRecording')

# Set test environment variables
os.environ['PHANTOM_PUBLIC_KEY'] = 'DxPv2QMA5cWR5Xj6N3qwW7BQEqWQCgHGk7JqhwfKKgRY'  # Test public key
os.environ['NETWORK'] = 'devnet'  # Use devnet for testing
os.environ['RPC_URL'] = 'https://api.devnet.solana.com'
os.environ['SLIPPAGE_BPS'] = '50'
os.environ['MIN_SOL_BALANCE'] = '0.05'
os.environ['MAX_POSITION_SIZE'] = '0.2'
os.environ['DAILY_LOSS_LIMIT'] = '0.05'
os.environ['MAX_DRAWDOWN'] = '0.1'

class MockWallet:
    def __init__(self):
        self.is_connected = True
        
    async def connect(self):
        self.is_connected = True
        return True
        
    async def close(self):
        self.is_connected = False
        pass
        
    async def get_balance(self, token_address=None):
        return 1.0  # Mock balance
        
    async def get_token_accounts(self):
        return []  # Mock empty token accounts
        
    async def execute_transaction(self, transaction):
        return {'success': True, 'signature': 'mock_signature'}

class MockTradingEngine:
    async def execute_trade(self, from_token, to_token, amount):
        # Mock successful trade execution
        return type('Trade', (), {
            'success': True,
            'from_token': from_token,
            'to_token': to_token,
            'amount': amount,
            'price': 100.0,
            'timestamp': datetime.now(),
            'signature': 'mock_signature',
            'fee': 0.1
        })

class MockRiskManager:
    def __init__(self):
        self._positions = []
        self._portfolio_value = 1.0
        
    async def get_positions(self):
        return self._positions
        
    async def get_portfolio_stats(self):
        return {
            'portfolio_value': self._portfolio_value,
            'daily_pnl': 0.0,
            'daily_trades': 0,
            'drawdown': 0.0,
            'positions': len(self._positions),
            'realized_pnl': 0,
            'unrealized_pnl': 0
        }
        
    def update_position(self, trade):
        # Mock position update
        if trade.from_token == "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB":  # USDT
            # Buy position
            self._positions.append({
                'token': trade.to_token,
                'size': trade.amount,
                'entry_price': trade.price,
                'current_price': trade.price,
                'unrealized_pnl': 0.0,
                'timestamp': trade.timestamp
            })
        else:
            # Sell position
            if self._positions:
                self._positions.pop()  # Remove last position

async def test_trade_recording():
    try:
        bot = TradingBot()
        bot.wallet = MockWallet()  # Replace with mock wallet
        await bot.initialize()
        bot.trading_engine = MockTradingEngine()  # Replace with mock trading engine
        bot.risk_manager = MockRiskManager()  # Replace with mock risk manager
        
        # Test token addresses
        sol_address = "So11111111111111111111111111111111111111112"  # SOL
        usdt_address = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"  # USDT
        
        # Execute a series of trades
        logger.info("Testing trade execution and recording...")
        
        # Test 1: Buy SOL with USDT
        trade1 = await bot.trading_engine.execute_trade(usdt_address, sol_address, 0.01)
        if trade1.success:
            logger.info(f"Successfully executed buy trade: {trade1}")
            bot.risk_manager.update_position(trade1)
            
            # Verify position was created
            positions = await bot.risk_manager.get_positions()
            if positions:
                logger.info(f"Position created: {positions[0]}")
                
                # Test 2: Add to position
                trade2 = await bot.trading_engine.execute_trade(usdt_address, sol_address, 0.005)
                if trade2.success:
                    logger.info(f"Successfully added to position: {trade2}")
                    bot.risk_manager.update_position(trade2)
                    
                    # Verify position was updated
                    updated_positions = await bot.risk_manager.get_positions()
                    if updated_positions:
                        logger.info(f"Updated position: {updated_positions[0]}")
                        
                        # Test 3: Partial close
                        trade3 = await bot.trading_engine.execute_trade(sol_address, usdt_address, 0.0075)
                        if trade3.success:
                            logger.info(f"Successfully executed partial close: {trade3}")
                            bot.risk_manager.update_position(trade3)
                            
                            # Test 4: Close remaining position
                            remaining_amount = updated_positions[0]['size'] - 0.0075
                            trade4 = await bot.trading_engine.execute_trade(sol_address, usdt_address, remaining_amount)
                            if trade4.success:
                                logger.info(f"Successfully closed position: {trade4}")
                                bot.risk_manager.update_position(trade4)
        
        # Test 5: Update risk metrics
        metrics = await bot.risk_manager.get_portfolio_stats()
        if metrics:
            logger.info(f"Successfully updated risk metrics: {metrics}")
        
        # Get trade history from database
        db = Database()
        trades = db.get_trades()
        logger.info(f"\nTrade history:")
        for trade in trades:
            logger.info(trade)
        
        # Get performance summary
        summary = await bot.risk_manager.get_portfolio_stats()
        logger.info(f"\nPerformance summary: {summary}")
        
        await bot.cleanup()
        
    except Exception as e:
        logger.error(f"Error in trade recording test: {str(e)}")
        raise e

if __name__ == "__main__":
    if platform.system() == 'Windows':
        # Set up proper event loop policy for Windows
        if sys.version_info[0] == 3 and sys.version_info[1] >= 8:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(test_trade_recording())
