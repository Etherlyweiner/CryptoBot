"""Sniper bot for automated trading"""
import logging
import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
from .token_scanner import TokenScanner
from .monitoring.logger import BotLogger

logger = logging.getLogger(__name__)

class SniperBot:
    """Bot for sniping new token listings"""
    
    def __init__(self, config: Dict):
        """Initialize sniper bot"""
        self.config = config
        self.scanner = TokenScanner(config)
        self.active_positions = {}
        self.token_cache = {}
        self.logger = BotLogger()
        
        # Trading parameters
        self.min_liquidity = config.get('min_liquidity', 100000)  # Minimum liquidity in USD
        self.min_market_cap = config.get('min_market_cap', 1000000)  # Minimum market cap in USD
        self.max_position_size = config.get('max_position_size', 1.0)  # Maximum position size in SOL
        self.take_profit = config.get('take_profit', 0.1)  # Take profit percentage
        self.stop_loss = config.get('stop_loss', 0.05)  # Stop loss percentage
        self.trailing_stop = config.get('trailing_stop', 0.05)  # Trailing stop percentage
        
        # Cache settings
        self.cache_duration = config.get('cache_duration', 300)  # Cache duration in seconds
    
    async def __aenter__(self):
        """Async context manager enter"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass
    
    async def get_token_info(self, token_address: str) -> Optional[Dict]:
        """Get token information with caching"""
        try:
            # Check cache first
            if token_address in self.token_cache:
                cache_time, token_info = self.token_cache[token_address]
                if datetime.now() - cache_time < timedelta(seconds=self.cache_duration):
                    return token_info
            
            # Get fresh data
            async with self.scanner as scanner:
                token_info = await scanner.get_token_info(token_address)
                if token_info:
                    self.token_cache[token_address] = (datetime.now(), token_info)
                return token_info
                
        except Exception as e:
            logger.error(f"Error getting token info: {str(e)}")
            return None
    
    async def check_position(self, token_address: str, entry_price: float, current_price: float) -> str:
        """Check position status and determine action"""
        try:
            # Calculate price change
            price_change = (current_price - entry_price) / entry_price
            
            # Initialize position tracking if needed
            if token_address not in self.active_positions:
                self.active_positions[token_address] = {
                    'entry_price': entry_price,
                    'highest_price': current_price,
                    'trailing_stop_active': False
                }
            
            position = self.active_positions[token_address]
            
            # Check take profit first
            if price_change >= self.take_profit:
                return 'sell'
            
            # Check stop loss
            if price_change <= -self.stop_loss:
                return 'sell'
            
            # Update highest price and trailing stop status
            if current_price > position['highest_price']:
                position['highest_price'] = current_price
                # Activate trailing stop if we're in profit
                if current_price > entry_price:
                    position['trailing_stop_active'] = True
            
            # Check trailing stop only if active
            if position['trailing_stop_active']:
                trailing_stop_price = position['highest_price'] * (1 - self.trailing_stop)
                if current_price < trailing_stop_price:
                    return 'sell'
            
            return 'hold'
            
        except Exception as e:
            logger.error(f"Error checking position: {str(e)}")
            return 'error'
    
    async def validate_position(self, token_address: str, position_size: float) -> bool:
        """Validate if position meets trading criteria"""
        try:
            token_info = await self.get_token_info(token_address)
            if not token_info:
                return False
            
            # Check liquidity
            if token_info.get('liquidity_usd', 0) < self.min_liquidity:
                logger.info(f"Insufficient liquidity: {token_info.get('liquidity_usd')}")
                return False
            
            # Check market cap
            if token_info.get('market_cap', 0) < self.min_market_cap:
                logger.info(f"Insufficient market cap: {token_info.get('market_cap')}")
                return False
            
            # Check position size
            if position_size > self.max_position_size:
                logger.info(f"Position size too large: {position_size}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating position: {str(e)}")
            return False
