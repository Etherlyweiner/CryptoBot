"""Base exchange interface for CryptoBot."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from decimal import Decimal
import asyncio
from datetime import datetime
import logging
from dataclasses import dataclass

logger = logging.getLogger('Exchange')

@dataclass
class OrderBook:
    """Order book data structure."""
    bids: List[tuple[Decimal, Decimal]]  # price, amount
    asks: List[tuple[Decimal, Decimal]]  # price, amount
    timestamp: datetime

@dataclass
class Trade:
    """Trade data structure."""
    id: str
    symbol: str
    side: str
    price: Decimal
    amount: Decimal
    timestamp: datetime
    fee: Optional[Decimal] = None
    fee_currency: Optional[str] = None

@dataclass
class Position:
    """Position data structure."""
    symbol: str
    side: str
    amount: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    liquidation_price: Optional[Decimal] = None

class ExchangeInterface(ABC):
    """Abstract base class for exchange implementations."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize exchange interface."""
        self.config = config
        self.name = config.get('name', 'unknown')
        
    @abstractmethod
    async def get_markets(self) -> Dict[str, Dict]:
        """Get available markets and their properties."""
        pass
        
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Decimal]:
        """Get current ticker for symbol."""
        pass
        
    @abstractmethod
    async def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        """Get order book for symbol."""
        pass
        
    @abstractmethod
    async def get_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """Get recent trades for symbol."""
        pass
        
    @abstractmethod
    async def get_ohlcv(self,
                       symbol: str,
                       timeframe: str,
                       since: Optional[datetime] = None,
                       limit: int = 100) -> List[Dict]:
        """Get OHLCV candlestick data."""
        pass
        
    @abstractmethod
    async def create_order(self,
                         symbol: str,
                         order_type: str,
                         side: str,
                         amount: Decimal,
                         price: Optional[Decimal] = None) -> Dict:
        """Create a new order."""
        pass
        
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order."""
        pass
        
    @abstractmethod
    async def get_order(self, order_id: str, symbol: str) -> Dict:
        """Get order details."""
        pass
        
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get open orders."""
        pass
        
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get current positions."""
        pass
        
    @abstractmethod
    async def get_balance(self, currency: Optional[str] = None) -> Dict[str, Decimal]:
        """Get account balance."""
        pass
        
    async def get_position_risk(self, position: Position) -> Dict[str, Decimal]:
        """Calculate position risk metrics."""
        return {
            'unrealized_pnl': position.unrealized_pnl,
            'liquidation_risk': (
                abs(position.current_price - position.liquidation_price)
                / position.current_price
                if position.liquidation_price
                else Decimal('0')
            ),
            'position_size': abs(position.amount * position.current_price),
            'entry_value': abs(position.amount * position.entry_price)
        }
        
    async def get_market_impact(self,
                              symbol: str,
                              side: str,
                              amount: Decimal) -> Decimal:
        """Calculate market impact for a potential trade."""
        orderbook = await self.get_orderbook(symbol)
        orders = orderbook.bids if side == 'sell' else orderbook.asks
        
        remaining = amount
        weighted_price = Decimal('0')
        
        for price, size in orders:
            if remaining <= 0:
                break
            filled = min(remaining, size)
            weighted_price += price * filled
            remaining -= filled
            
        if remaining > 0:
            return Decimal('inf')  # Not enough liquidity
            
        return abs(weighted_price / amount - orders[0][0]) / orders[0][0]
        
    async def get_funding_info(self, symbol: str) -> Dict[str, Decimal]:
        """Get funding rate information for perpetual contracts."""
        return {
            'current_rate': Decimal('0'),
            'predicted_rate': Decimal('0'),
            'next_funding_time': None
        }
        
    async def get_leverage_tiers(self, symbol: str) -> List[Dict]:
        """Get leverage tier information."""
        return []
        
    async def set_leverage(self,
                         symbol: str,
                         leverage: int) -> bool:
        """Set leverage for symbol."""
        return False
        
    def validate_order(self,
                      symbol: str,
                      order_type: str,
                      side: str,
                      amount: Decimal,
                      price: Optional[Decimal] = None) -> List[str]:
        """Validate order parameters."""
        errors = []
        
        if amount <= 0:
            errors.append("Order amount must be positive")
            
        if order_type == 'limit' and (not price or price <= 0):
            errors.append("Limit orders require a valid price")
            
        return errors
        
    async def close(self):
        """Clean up exchange resources."""
        pass
