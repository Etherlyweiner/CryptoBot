from decimal import Decimal
import pandas as pd
from typing import Dict, Optional, List, Tuple
import logging
from dataclasses import dataclass
from risk_management import RiskManager, Position
import uuid

logger = logging.getLogger('TradingExecution')

@dataclass
class OrderResult:
    """Data class for order execution results."""
    success: bool
    order_id: Optional[str] = None
    error_message: Optional[str] = None
    filled_price: Optional[Decimal] = None
    filled_quantity: Optional[Decimal] = None

class TradingExecutor:
    """Handles trade execution and order management."""
    
    def __init__(self,
                 risk_manager: RiskManager,
                 max_slippage: Decimal = Decimal('0.001'),  # 0.1% max slippage
                 min_order_interval: int = 60,  # Minimum seconds between orders
                 max_retries: int = 3,  # Maximum order retries
                 use_db: bool = True):
        """Initialize trading executor."""
        self.risk_manager = risk_manager
        self.max_slippage = max_slippage
        self.min_order_interval = min_order_interval
        self.max_retries = max_retries
        self.pending_orders: Dict[str, Dict] = {}
        self._last_order_time: Dict[str, pd.Timestamp] = {}
        
        # Database session
        self.use_db = use_db
        if use_db:
            from database import Session
            self.db_session = Session()
            
    def __del__(self):
        """Cleanup database session."""
        if hasattr(self, 'db_session'):
            self.db_session.close()
            
    def place_order(self,
                   symbol: str,
                   side: str,
                   price: Decimal,
                   size: Decimal,
                   confidence: Optional[Decimal] = None) -> OrderResult:
        """Place a new order with improved error handling."""
        try:
            # Validate inputs
            if not isinstance(price, Decimal) or not isinstance(size, Decimal):
                return OrderResult(
                    success=False,
                    error_message="Price and size must be Decimal types"
                )
                
            if size <= 0:
                return OrderResult(
                    success=False,
                    error_message="Order size must be positive"
                )
                
            # Check order interval
            current_time = pd.Timestamp.now()
            if symbol in self._last_order_time:
                time_since_last = (current_time - self._last_order_time[symbol]).total_seconds()
                if time_since_last < self.min_order_interval:
                    return OrderResult(
                        success=False,
                        error_message=f"Order interval too short: {time_since_last:.1f}s < {self.min_order_interval}s"
                    )
                    
            # Check risk limits with detailed error message
            can_open, reason = self.risk_manager.can_open_position(symbol, price, size)
            if not can_open:
                return OrderResult(
                    success=False,
                    error_message=f"Risk check failed: {reason}"
                )
                
            # Generate order ID and create order
            order_id = str(uuid.uuid4())
            order = {
                'id': order_id,
                'symbol': symbol,
                'side': side,
                'price': price,
                'size': size,
                'status': 'pending',
                'timestamp': current_time,
                'confidence': confidence
            }
            
            # Store order and update last order time
            self.pending_orders[order_id] = order
            self._last_order_time[symbol] = current_time
            
            # Record in database if enabled
            if self.use_db:
                from database import Trade
                db_trade = Trade(
                    symbol=symbol,
                    side=side,
                    entry_price=float(price),
                    quantity=float(size),
                    timestamp=current_time
                )
                self.db_session.add(db_trade)
                self.db_session.commit()
                
            return OrderResult(
                success=True,
                order_id=order_id
            )
            
        except Exception as e:
            logger.exception("Error placing order")
            return OrderResult(
                success=False,
                error_message=f"Internal error: {str(e)}"
            )
            
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        if order_id not in self.pending_orders:
            return False
            
        if self.pending_orders[order_id]['status'] != 'pending':
            return False
            
        # TODO: Implement actual order cancellation with exchange API
        self.pending_orders[order_id]['status'] = 'cancelled'
        return True
        
    def update_order_status(self, order_id: str) -> Optional[Dict]:
        """Get current status of an order."""
        if order_id not in self.pending_orders:
            return None
            
        # TODO: Implement actual order status check with exchange API
        return self.pending_orders[order_id]
        
    def handle_order_filled(self,
                          order_id: str,
                          filled_price: Decimal,
                          filled_quantity: Decimal) -> None:
        """Handle order fill with improved error handling."""
        try:
            if order_id not in self.pending_orders:
                logger.error(f"Unknown order ID: {order_id}")
                return
                
            order = self.pending_orders[order_id]
            symbol = order['symbol']
            side = order['side']
            
            # Validate fill price
            expected_price = order['price']
            price_diff = abs(filled_price - expected_price) / expected_price
            if price_diff > self.max_slippage:
                logger.warning(
                    f"High slippage detected: {float(price_diff):.2%} > {float(self.max_slippage):.2%}"
                )
                
            # Create position
            position = Position(
                symbol=symbol,
                side=side,
                entry_price=filled_price,
                quantity=filled_quantity,
                timestamp=pd.Timestamp.now()
            )
            
            # Update risk manager
            self.risk_manager.positions[symbol] = position
            self.risk_manager.record_trade({
                'symbol': symbol,
                'side': side,
                'entry_price': filled_price,
                'size': filled_quantity,
                'time': position.timestamp
            })
            
            # Clean up
            del self.pending_orders[order_id]
            
        except Exception as e:
            logger.exception("Error handling order fill")
            raise
            
    def execute_trade_signal(self,
                           symbol: str,
                           signal_type: str,
                           price: Decimal,
                           confidence: Decimal) -> Optional[str]:
        """
        Execute a trade based on a signal.
        
        Args:
            symbol: Trading pair symbol
            signal_type: Type of signal ('long' or 'short')
            price: Current price
            confidence: Signal confidence score (0-1)
            
        Returns:
            Order ID if order placed successfully, None otherwise
        """
        # Skip low confidence signals
        if confidence < Decimal('0.7'):
            logger.info(f"Skipping low confidence signal: {float(confidence):.2f}")
            return None
            
        # Calculate position size based on confidence
        base_size = Decimal('1.0')  # Base position size
        size = base_size * confidence  # Scale by confidence
        
        # Check if we can open position
        if signal_type == 'long':
            # Skip if we already have a position
            if symbol in self.risk_manager.positions:
                logger.warning(f"Position already exists for {symbol}")
                return None
                
            can_open, reason = self.risk_manager.can_open_position(symbol, price, size)
            if not can_open:
                logger.warning(f"Cannot open position: {reason}")
                return None
                
            # Place buy order
            result = self.place_order(
                symbol=symbol,
                side='buy',
                price=price,
                size=size,
                confidence=confidence
            )
            
        else:  # short signal
            # Skip if we don't have a position to close
            if symbol not in self.risk_manager.positions:
                logger.warning(f"No position to close for {symbol}")
                return None
                
            # Place sell order
            result = self.place_order(
                symbol=symbol,
                side='sell',
                price=price,
                size=self.risk_manager.positions[symbol].quantity,
                confidence=confidence
            )
            
        if result.success:
            logger.info(
                f"Placed {signal_type} order for {symbol} at {float(price):.2f}, "
                f"size: {float(size):.4f}, confidence: {float(confidence):.2f}"
            )
            return result.order_id
            
        logger.error(f"Order failed: {result.error_message}")
        return None
