"""Token price monitoring module."""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Optional, Set

from .api.jupiter_client import JupiterClient

logger = logging.getLogger(__name__)

class PriceMonitor:
    """Monitor token prices and detect significant changes."""
    
    def __init__(self, jupiter_client: JupiterClient, update_interval: int = 60):
        """Initialize price monitor.
        
        Args:
            jupiter_client: Jupiter API client
            update_interval: Price update interval in seconds
        """
        self.jupiter = jupiter_client
        self.update_interval = update_interval
        self.prices: Dict[str, Dict] = {}  # token_address -> price data
        self.monitored_tokens: Set[str] = set()
        self.running = False
        self._task: Optional[asyncio.Task] = None
        
    def add_token(self, token_address: str):
        """Add token to monitor.
        
        Args:
            token_address: Token address to monitor
        """
        self.monitored_tokens.add(token_address)
        
    def remove_token(self, token_address: str):
        """Remove token from monitoring.
        
        Args:
            token_address: Token address to remove
        """
        self.monitored_tokens.discard(token_address)
        self.prices.pop(token_address, None)
        
    async def start(self):
        """Start price monitoring."""
        if self.running:
            return
            
        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Price monitoring started")
        
    async def stop(self):
        """Stop price monitoring."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Price monitoring stopped")
        
    def get_price(self, token_address: str) -> Optional[Dict]:
        """Get current price data for a token.
        
        Args:
            token_address: Token address
            
        Returns:
            Price data if available
        """
        return self.prices.get(token_address)
        
    async def _monitor_loop(self):
        """Main monitoring loop."""
        try:
            while self.running:
                try:
                    await self._update_prices()
                except Exception as e:
                    logger.error(f"Error updating prices: {str(e)}")
                    
                await asyncio.sleep(self.update_interval)
                
        except asyncio.CancelledError:
            logger.info("Price monitoring loop cancelled")
            raise
            
        except Exception as e:
            logger.exception(f"Error in price monitoring loop: {str(e)}")
            raise
            
    async def _update_prices(self):
        """Update prices for all monitored tokens."""
        if not self.monitored_tokens:
            return
            
        # Get WSOL price as reference
        wsol_price = Decimal('1.0')  # 1 WSOL = 1 SOL
        
        # Update prices for each token
        for token_address in self.monitored_tokens:
            try:
                # Get current price
                price = await self.jupiter.get_price(token_address, 'So11111111111111111111111111111111111111112')
                if price is None:
                    continue
                    
                # Calculate price change
                old_price = self.prices.get(token_address, {}).get('price', price)
                price_change = ((price - old_price) / old_price) * 100 if old_price else 0
                
                # Update price data
                self.prices[token_address] = {
                    'price': price,
                    'priceChange': float(price_change),
                    'timestamp': asyncio.get_event_loop().time(),
                    'priceInSol': float(price * wsol_price)
                }
                
                # Log significant price changes
                if abs(price_change) >= 5.0:  # 5% threshold
                    logger.info(f"Significant price change for {token_address}: {price_change:+.2f}%")
                    
            except Exception as e:
                logger.error(f"Error updating price for {token_address}: {str(e)}")
                
    def get_all_prices(self) -> Dict[str, Dict]:
        """Get all current prices.
        
        Returns:
            Dict mapping token addresses to price data
        """
        return self.prices.copy()
