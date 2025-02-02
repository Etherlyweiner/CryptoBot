"""Binance exchange implementation."""

from typing import Dict, List, Optional, Any
from decimal import Decimal
import asyncio
from datetime import datetime
import logging
import hmac
import hashlib
import time
import aiohttp
from urllib.parse import urlencode
import json

from .base import (
    ExchangeInterface,
    OrderBook,
    Trade,
    Position
)

logger = logging.getLogger('BinanceExchange')

class BinanceExchange(ExchangeInterface):
    """Binance exchange implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Binance exchange."""
        super().__init__(config)
        
        self.api_key = config['api_key']
        self.api_secret = config['api_secret']
        self.testnet = config.get('testnet', False)
        
        # API URLs
        self.base_url = (
            'https://testnet.binance.vision/api'
            if self.testnet
            else 'https://api.binance.com/api'
        )
        
        self.session = aiohttp.ClientSession()
        
    def _generate_signature(self, params: Dict) -> str:
        """Generate signature for authenticated requests."""
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
    async def _public_request(self,
                            method: str,
                            path: str,
                            params: Optional[Dict] = None) -> Any:
        """Make public API request."""
        url = f"{self.base_url}{path}"
        try:
            async with self.session.request(
                method,
                url,
                params=params
            ) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 5))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    return await self._public_request(method, path, params)
                    
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {e}")
            raise
            
    async def _private_request(self,
                             method: str,
                             path: str,
                             params: Optional[Dict] = None) -> Any:
        """Make private authenticated API request."""
        params = params or {}
        params['timestamp'] = int(time.time() * 1000)
        params['signature'] = self._generate_signature(params)
        
        headers = {'X-MBX-APIKEY': self.api_key}
        
        try:
            async with self.session.request(
                method,
                f"{self.base_url}{path}",
                params=params,
                headers=headers
            ) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 5))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    return await self._private_request(method, path, params)
                    
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {e}")
            raise
            
    async def get_markets(self) -> Dict[str, Dict]:
        """Get available markets and their properties."""
        response = await self._public_request('GET', '/v3/exchangeInfo')
        
        markets = {}
        for symbol in response['symbols']:
            markets[symbol['symbol']] = {
                'base': symbol['baseAsset'],
                'quote': symbol['quoteAsset'],
                'status': symbol['status'],
                'min_price': Decimal(symbol['filters'][0]['minPrice']),
                'max_price': Decimal(symbol['filters'][0]['maxPrice']),
                'tick_size': Decimal(symbol['filters'][0]['tickSize']),
                'min_qty': Decimal(symbol['filters'][1]['minQty']),
                'max_qty': Decimal(symbol['filters'][1]['maxQty']),
                'step_size': Decimal(symbol['filters'][1]['stepSize'])
            }
        return markets
        
    async def get_ticker(self, symbol: str) -> Dict[str, Decimal]:
        """Get current ticker for symbol."""
        response = await self._public_request(
            'GET',
            '/v3/ticker/24hr',
            {'symbol': symbol}
        )
        
        return {
            'symbol': symbol,
            'last': Decimal(response['lastPrice']),
            'bid': Decimal(response['bidPrice']),
            'ask': Decimal(response['askPrice']),
            'volume': Decimal(response['volume']),
            'change': Decimal(response['priceChangePercent'])
        }
        
    async def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        """Get order book for symbol."""
        response = await self._public_request(
            'GET',
            '/v3/depth',
            {
                'symbol': symbol,
                'limit': depth
            }
        )
        
        return OrderBook(
            bids=[
                (Decimal(price), Decimal(amount))
                for price, amount in response['bids']
            ],
            asks=[
                (Decimal(price), Decimal(amount))
                for price, amount in response['asks']
            ],
            timestamp=datetime.fromtimestamp(response['lastUpdateId'] / 1000)
        )
        
    async def get_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """Get recent trades for symbol."""
        response = await self._public_request(
            'GET',
            '/v3/trades',
            {
                'symbol': symbol,
                'limit': limit
            }
        )
        
        return [
            Trade(
                id=str(trade['id']),
                symbol=symbol,
                side='buy' if trade['isBuyerMaker'] else 'sell',
                price=Decimal(trade['price']),
                amount=Decimal(trade['qty']),
                timestamp=datetime.fromtimestamp(trade['time'] / 1000)
            )
            for trade in response
        ]
        
    async def get_ohlcv(self,
                       symbol: str,
                       timeframe: str,
                       since: Optional[datetime] = None,
                       limit: int = 100) -> List[Dict]:
        """Get OHLCV candlestick data."""
        intervals = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }
        
        params = {
            'symbol': symbol,
            'interval': intervals.get(timeframe, '1h'),
            'limit': limit
        }
        
        if since:
            params['startTime'] = int(since.timestamp() * 1000)
            
        response = await self._public_request('GET', '/v3/klines', params)
        
        return [
            {
                'timestamp': datetime.fromtimestamp(candle[0] / 1000),
                'open': Decimal(candle[1]),
                'high': Decimal(candle[2]),
                'low': Decimal(candle[3]),
                'close': Decimal(candle[4]),
                'volume': Decimal(candle[5])
            }
            for candle in response
        ]
        
    async def create_order(self,
                         symbol: str,
                         order_type: str,
                         side: str,
                         amount: Decimal,
                         price: Optional[Decimal] = None) -> Dict:
        """Create a new order."""
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': str(amount)
        }
        
        if order_type == 'limit':
            if not price:
                raise ValueError("Limit orders require a price")
            params['price'] = str(price)
            params['timeInForce'] = 'GTC'
            
        response = await self._private_request('POST', '/v3/order', params)
        
        return {
            'id': str(response['orderId']),
            'symbol': response['symbol'],
            'side': response['side'].lower(),
            'type': response['type'].lower(),
            'price': Decimal(response['price']) if response['price'] != '0' else None,
            'amount': Decimal(response['origQty']),
            'filled': Decimal(response['executedQty']),
            'status': response['status'].lower()
        }
        
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order."""
        try:
            await self._private_request(
                'DELETE',
                '/v3/order',
                {
                    'symbol': symbol,
                    'orderId': order_id
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return False
            
    async def get_order(self, order_id: str, symbol: str) -> Dict:
        """Get order details."""
        response = await self._private_request(
            'GET',
            '/v3/order',
            {
                'symbol': symbol,
                'orderId': order_id
            }
        )
        
        return {
            'id': str(response['orderId']),
            'symbol': response['symbol'],
            'side': response['side'].lower(),
            'type': response['type'].lower(),
            'price': Decimal(response['price']) if response['price'] != '0' else None,
            'amount': Decimal(response['origQty']),
            'filled': Decimal(response['executedQty']),
            'status': response['status'].lower(),
            'timestamp': datetime.fromtimestamp(response['time'] / 1000)
        }
        
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get open orders."""
        params = {}
        if symbol:
            params['symbol'] = symbol
            
        response = await self._private_request('GET', '/v3/openOrders', params)
        
        return [
            {
                'id': str(order['orderId']),
                'symbol': order['symbol'],
                'side': order['side'].lower(),
                'type': order['type'].lower(),
                'price': Decimal(order['price']) if order['price'] != '0' else None,
                'amount': Decimal(order['origQty']),
                'filled': Decimal(order['executedQty']),
                'status': order['status'].lower(),
                'timestamp': datetime.fromtimestamp(order['time'] / 1000)
            }
            for order in response
        ]
        
    async def get_positions(self) -> List[Position]:
        """Get current positions."""
        response = await self._private_request('GET', '/v3/account')
        
        positions = []
        for balance in response['balances']:
            amount = Decimal(balance['free']) + Decimal(balance['locked'])
            if amount > 0:
                # For spot trading, we consider non-zero balances as positions
                ticker = await self.get_ticker(f"{balance['asset']}USDT")
                positions.append(
                    Position(
                        symbol=balance['asset'],
                        side='long',
                        amount=amount,
                        entry_price=Decimal('0'),  # Not applicable for spot
                        current_price=ticker['last'],
                        unrealized_pnl=Decimal('0')  # Not applicable for spot
                    )
                )
        return positions
        
    async def get_balance(self, currency: Optional[str] = None) -> Dict[str, Decimal]:
        """Get account balance."""
        response = await self._private_request('GET', '/v3/account')
        
        balances = {}
        for balance in response['balances']:
            if currency and balance['asset'] != currency:
                continue
            balances[balance['asset']] = {
                'free': Decimal(balance['free']),
                'used': Decimal(balance['locked']),
                'total': Decimal(balance['free']) + Decimal(balance['locked'])
            }
            
        return balances
        
    async def close(self):
        """Clean up exchange resources."""
        await self.session.close()
