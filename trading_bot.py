"""Main trading bot implementation."""

import asyncio
import logging
from typing import Dict, List, Optional
from decimal import Decimal
import json
from datetime import datetime
from dataclasses import dataclass

from exchanges.base import ExchangeInterface
from exchanges.binance import BinanceExchange
from cache_manager import cache_manager, market_cache
from metrics_collector import metrics
from system_health import health_checker
from security_manager import security_manager

logger = logging.getLogger('TradingBot')

@dataclass
class TradingConfig:
    """Trading configuration."""
    symbol: str
    base_currency: str
    quote_currency: str
    position_size: Decimal
    max_positions: int
    stop_loss_pct: Decimal
    take_profit_pct: Decimal
    max_slippage_pct: Decimal
    order_timeout: int = 30

class TradingBot:
    """Conservative trading bot implementation."""
    
    def __init__(self,
                 exchange: ExchangeInterface,
                 config: TradingConfig):
        """Initialize trading bot."""
        self.exchange = exchange
        self.config = config
        self.is_running = False
        self.positions = {}
        
        # Initialize metrics
        self.trade_count = metrics.trade_count
        self.position_value = metrics.position_value
        self.pnl = metrics.pnl
        
    @market_cache.cached_price
    async def get_current_price(self, symbol: str) -> Decimal:
        """Get current price with caching."""
        ticker = await self.exchange.get_ticker(symbol)
        return ticker['last']
        
    async def can_open_position(self) -> bool:
        """Check if we can open a new position."""
        # Check number of positions
        if len(self.positions) >= self.config.max_positions:
            return False
            
        # Check system health
        health_metrics = await health_checker.get_health_metrics()
        if health_metrics.cpu_percent > 80 or health_metrics.memory_percent > 80:
            logger.warning("System resources too high to open position")
            return False
            
        # Check exchange connection
        try:
            await self.exchange.get_balance()
            return True
        except Exception as e:
            logger.error(f"Exchange connection error: {e}")
            return False
            
    async def calculate_position_size(self, price: Decimal) -> Decimal:
        """Calculate position size based on current conditions."""
        balance = await self.exchange.get_balance(self.config.quote_currency)
        available = balance[self.config.quote_currency]['free']
        
        # Use configured position size percentage
        size = available * self.config.position_size
        
        # Convert to base currency
        return size / price
        
    async def place_order(self,
                         side: str,
                         size: Decimal,
                         price: Optional[Decimal] = None) -> Dict:
        """Place an order with retry logic."""
        for attempt in range(3):
            try:
                order = await self.exchange.create_order(
                    symbol=self.config.symbol,
                    order_type='market' if price is None else 'limit',
                    side=side,
                    amount=size,
                    price=price
                )
                
                # Update metrics
                self.trade_count.labels(
                    symbol=self.config.symbol,
                    side=side
                ).inc()
                
                return order
                
            except Exception as e:
                logger.error(f"Order placement failed (attempt {attempt + 1}): {e}")
                if attempt == 2:
                    raise
                await asyncio.sleep(1)
                
    async def open_position(self):
        """Open a new position."""
        if not await self.can_open_position():
            return
            
        try:
            # Get current price
            price = await self.get_current_price(self.config.symbol)
            
            # Calculate position size
            size = await self.calculate_position_size(price)
            
            # Place market buy order
            order = await self.place_order('buy', size)
            
            # Set stop loss and take profit orders
            stop_price = price * (1 - self.config.stop_loss_pct)
            target_price = price * (1 + self.config.take_profit_pct)
            
            await asyncio.gather(
                self.place_order('sell', size, stop_price),
                self.place_order('sell', size, target_price)
            )
            
            # Track position
            self.positions[order['id']] = {
                'entry_price': price,
                'size': size,
                'stop_loss': stop_price,
                'take_profit': target_price
            }
            
            # Update metrics
            self.position_value.labels(symbol=self.config.symbol).set(
                float(price * size)
            )
            
            logger.info(f"Opened position: {order['id']}")
            
        except Exception as e:
            logger.error(f"Failed to open position: {e}")
            
    async def close_position(self, position_id: str):
        """Close an existing position."""
        if position_id not in self.positions:
            return
            
        try:
            position = self.positions[position_id]
            
            # Place market sell order
            await self.place_order('sell', position['size'])
            
            # Calculate P&L
            exit_price = await self.get_current_price(self.config.symbol)
            pnl = (exit_price - position['entry_price']) * position['size']
            
            # Update metrics
            self.pnl.labels(symbol=self.config.symbol).inc(float(pnl))
            self.position_value.labels(symbol=self.config.symbol).dec(
                float(position['entry_price'] * position['size'])
            )
            
            # Remove position
            del self.positions[position_id]
            
            logger.info(f"Closed position {position_id} with PnL: {pnl}")
            
        except Exception as e:
            logger.error(f"Failed to close position {position_id}: {e}")
            
    async def update_positions(self):
        """Update and manage existing positions."""
        current_price = await self.get_current_price(self.config.symbol)
        
        for position_id, position in list(self.positions.items()):
            # Check stop loss
            if current_price <= position['stop_loss']:
                logger.info(f"Stop loss triggered for position {position_id}")
                await self.close_position(position_id)
                
            # Check take profit
            elif current_price >= position['take_profit']:
                logger.info(f"Take profit triggered for position {position_id}")
                await self.close_position(position_id)
                
    async def run(self):
        """Main trading loop."""
        self.is_running = True
        
        try:
            while self.is_running:
                await self.update_positions()
                
                if await self.can_open_position():
                    await self.open_position()
                    
                await asyncio.sleep(1)  # Adjust based on exchange rate limits
                
        except Exception as e:
            logger.error(f"Trading loop error: {e}")
            self.is_running = False
            
        finally:
            # Clean up
            for position_id in list(self.positions.keys()):
                await self.close_position(position_id)
                
    async def stop(self):
        """Stop the trading bot."""
        self.is_running = False
        
# Example usage:
# config = TradingConfig(
#     symbol='BTC/USDT',
#     base_currency='BTC',
#     quote_currency='USDT',
#     position_size=Decimal('0.1'),  # 10% of available balance
#     max_positions=3,
#     stop_loss_pct=Decimal('0.02'),  # 2%
#     take_profit_pct=Decimal('0.05'),  # 5%
#     max_slippage_pct=Decimal('0.001')  # 0.1%
# )
# 
# exchange = BinanceExchange({
#     'api_key': 'your_api_key',
#     'api_secret': 'your_api_secret',
#     'testnet': True  # Use testnet for testing
# })
# 
# bot = TradingBot(exchange, config)
# await bot.run()
