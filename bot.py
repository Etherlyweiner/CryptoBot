"""
CryptoBot for Solana trading using Phantom wallet
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
import os
from datetime import datetime
import json
from dotenv import load_dotenv
from wallet import PhantomWallet, WalletError
from trading_engine import TradingEngine, TradeConfig, TradeResult
from risk_manager import RiskManager, RiskConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CryptoBot')

load_dotenv()

class TradingBot:
    def __init__(self):
        """Initialize the trading bot with all components"""
        self.wallet = PhantomWallet()
        self.trade_config = TradeConfig(
            slippage_bps=int(os.getenv('SLIPPAGE_BPS', '50')),
            min_sol_balance=float(os.getenv('MIN_SOL_BALANCE', '0.05'))
        )
        self.risk_config = RiskConfig(
            max_position_size=float(os.getenv('MAX_POSITION_SIZE', '0.2')),
            daily_loss_limit=float(os.getenv('DAILY_LOSS_LIMIT', '0.05')),
            max_drawdown=float(os.getenv('MAX_DRAWDOWN', '0.1'))
        )
        
        self.trading_engine = None
        self.risk_manager = None
        
        # Technical analysis parameters
        self.rsi_period = int(os.getenv('RSI_PERIOD', '14'))
        self.rsi_overbought = float(os.getenv('RSI_OVERBOUGHT', '70'))
        self.rsi_oversold = float(os.getenv('RSI_OVERSOLD', '30'))
        self.ema_fast = int(os.getenv('EMA_FAST', '12'))
        self.ema_slow = int(os.getenv('EMA_SLOW', '26'))
        self.macd_signal = int(os.getenv('MACD_SIGNAL', '9'))
        
        self.active_trades = {}
        self.analysis_results = {}
        
    async def initialize(self) -> bool:
        """Initialize all components of the trading bot"""
        try:
            logger.info("Initializing trading bot components...")
            
            # Connect wallet
            if not await self.wallet.connect():
                raise WalletError("Failed to connect wallet")
                
            # Initialize trading engine
            self.trading_engine = TradingEngine(self.wallet, self.trade_config)
            
            # Initialize risk manager
            self.risk_manager = RiskManager(self.wallet, self.risk_config)
            await self.risk_manager.initialize()
            
            logger.info("Trading bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize trading bot: {str(e)}")
            return False
        
    async def start(self):
        """Start the trading bot"""
        try:
            if not await self.initialize():
                raise Exception("Failed to initialize trading bot")
                
            logger.info("Starting trading bot...")
            
            while True:
                try:
                    # Update market data
                    await self.update_market_data()
                    
                    # Check for trading signals
                    await self.check_signals()
                    
                    # Manage existing positions
                    await self.manage_trades()
                    
                    # Log portfolio stats
                    stats = await self.risk_manager.get_portfolio_stats()
                    logger.info(f"Portfolio stats: {json.dumps(stats, indent=2)}")
                    
                    # Wait before next iteration
                    await asyncio.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}")
                    await asyncio.sleep(60)
                    
        except Exception as e:
            logger.error(f"Fatal error in trading bot: {str(e)}")
            raise
        finally:
            await self.cleanup()
            
    async def update_market_data(self):
        """Update market data for analysis"""
        try:
            tokens = await self.get_tradeable_tokens()
            for token in tokens[:10]:  # Only analyze top 10 tokens for now
                price_data = await self.get_price_history(token['address'])
                if price_data is not None:
                    self.analysis_results[token['address']] = self.analyze_token(token['address'], price_data)
        except Exception as e:
            logger.error(f"Error updating market data: {str(e)}")
            
    async def check_signals(self):
        """Check for trading signals and execute trades if conditions are met"""
        try:
            for token_address, analysis in self.analysis_results.items():
                # Skip if we already have a position
                if token_address in self.active_trades:
                    continue
                    
                # Check if we can trade
                can_trade, reason = await self.risk_manager.can_trade(token_address, 0)  # Amount will be calculated later
                if not can_trade:
                    logger.info(f"Trade not allowed for {token_address}: {reason}")
                    continue
                    
                # Get trading signal
                signal = self.get_trading_signal(analysis)
                if signal == 0:  # No signal
                    continue
                    
                # Calculate position size
                position_size = await self.risk_manager.calculate_position_size(token_address, analysis['price'])
                if not position_size:
                    continue
                    
                # Execute trade
                if signal > 0:  # Buy signal
                    result = await self.trading_engine.execute_trade(
                        "So11111111111111111111111111111111111111112",  # SOL
                        token_address,
                        position_size
                    )
                else:  # Sell signal
                    result = await self.trading_engine.execute_trade(
                        token_address,
                        "So11111111111111111111111111111111111111112",  # SOL
                        position_size
                    )
                    
                if result.success:
                    # Update position tracking
                    await self.risk_manager.update_position(token_address, {
                        'size': position_size,
                        'price': result.price,
                        'timestamp': result.timestamp
                    })
                    logger.info(f"Successfully executed trade for {token_address}")
                else:
                    logger.error(f"Trade failed for {token_address}: {result.error}")
                    
        except Exception as e:
            logger.error(f"Error checking trading signals: {str(e)}")
            
    def get_trading_signal(self, analysis: Dict) -> int:
        """Get trading signal from analysis results
        Returns:
            1 for buy signal
            -1 for sell signal
            0 for no signal
        """
        try:
            if not analysis:
                return 0
                
            # Example simple strategy using RSI and MACD
            rsi = analysis.get('rsi')
            macd = analysis.get('macd')
            macd_signal = analysis.get('macd_signal')
            
            if rsi and macd and macd_signal:
                if rsi < self.rsi_oversold and macd > macd_signal:
                    return 1  # Buy signal
                elif rsi > self.rsi_overbought and macd < macd_signal:
                    return -1  # Sell signal
                    
            return 0
            
        except Exception as e:
            logger.error(f"Error getting trading signal: {str(e)}")
            return 0
            
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.trading_engine:
                await self.trading_engine.close()
            if self.wallet:
                await self.wallet.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            
if __name__ == "__main__":
    bot = TradingBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
