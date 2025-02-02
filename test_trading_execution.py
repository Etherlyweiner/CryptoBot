import unittest
from decimal import Decimal
import pandas as pd
from risk_management import RiskManager
from trading_execution import TradingExecutor

class TestTradingExecutor(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.risk_manager = RiskManager(
            initial_capital=Decimal('1000'),
            max_position_size=Decimal('0.1'),  # 10%
            max_total_exposure=Decimal('0.5'),  # 50%
            max_drawdown=Decimal('0.15'),  # 15%
            risk_per_trade=Decimal('0.02'),  # 2%
            atr_period=14,
            stop_loss_atr_multiplier=Decimal('2.0'),
            take_profit_atr_multiplier=Decimal('3.0'),
            max_daily_trades=5,
            min_win_rate=Decimal('0.4'),
            correlation_threshold=Decimal('0.7')
        )
        
        self.executor = TradingExecutor(
            risk_manager=self.risk_manager,
            max_slippage=Decimal('0.001'),
            min_order_interval=0,  # No interval for testing
            max_retries=3
        )
        
    def test_order_placement(self):
        """Test basic order placement."""
        symbol = 'SOL/USD'
        price = Decimal('100')
        size = Decimal('0.5')  # 50% of max position size
        
        # Place buy order
        result = self.executor.place_order(
            symbol=symbol,
            side='buy',
            price=price,
            size=size
        )
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.order_id)
        self.assertEqual(float(result.filled_price), 100.0)
        self.assertEqual(float(result.filled_quantity), 0.5)
        
        # Verify order stored
        order = self.executor.open_orders[result.order_id]
        self.assertEqual(order['symbol'], symbol)
        self.assertEqual(order['side'], 'buy')
        self.assertEqual(float(order['price']), 100.0)
        self.assertEqual(float(order['size']), 0.5)
        
    def test_order_cancellation(self):
        """Test order cancellation."""
        symbol = 'SOL/USD'
        price = Decimal('100')
        size = Decimal('0.5')
        
        # Place order
        result = self.executor.place_order(
            symbol=symbol,
            side='buy',
            price=price,
            size=size
        )
        
        # Cancel order
        cancelled = self.executor.cancel_order(result.order_id)
        self.assertTrue(cancelled)
        
        # Verify order status
        order = self.executor.update_order_status(result.order_id)
        self.assertEqual(order['status'], 'cancelled')
        
    def test_signal_execution(self):
        """Test trade signal execution."""
        symbol = 'SOL/USD'
        price = Decimal('100')
        confidence = Decimal('0.8')
        
        # Execute long signal
        order_id = self.executor.execute_trade_signal(
            symbol=symbol,
            signal_type='long',
            price=price,
            confidence=confidence
        )
        
        self.assertIsNotNone(order_id)
        
        # Verify order details
        order = self.executor.open_orders[order_id]
        self.assertEqual(order['symbol'], symbol)
        self.assertEqual(order['side'], 'buy')
        self.assertEqual(float(order['price']), 100.0)
        
        # Simulate fill to create position
        self.executor.handle_order_filled(
            order_id=order_id,
            filled_price=price,
            filled_quantity=Decimal('0.8')  # Confidence * base_size
        )
        
        # Now execute short signal
        order_id = self.executor.execute_trade_signal(
            symbol=symbol,
            signal_type='short',
            price=price,
            confidence=confidence
        )
        
        self.assertIsNotNone(order_id)
        
        # Verify order details
        order = self.executor.open_orders[order_id]
        self.assertEqual(order['symbol'], symbol)
        self.assertEqual(order['side'], 'sell')
        
    def test_risk_limits(self):
        """Test risk management integration."""
        symbol = 'SOL/USD'
        price = Decimal('100')
        size = Decimal('1.5')  # Exceeds max position size
        
        # Attempt to place oversized order
        result = self.executor.place_order(
            symbol=symbol,
            side='buy',
            price=price,
            size=size
        )
        
        self.assertFalse(result.success)
        self.assertIn("Risk check failed", result.error_message)
        
    def test_order_interval(self):
        """Test minimum order interval."""
        # Create executor with 1 second interval
        executor = TradingExecutor(
            risk_manager=self.risk_manager,
            max_slippage=Decimal('0.001'),
            min_order_interval=1,
            max_retries=3
        )
        
        symbol = 'SOL/USD'
        price = Decimal('100')
        size = Decimal('0.1')
        
        # Place first order
        result1 = executor.place_order(
            symbol=symbol,
            side='buy',
            price=price,
            size=size
        )
        
        self.assertTrue(result1.success)
        
        # Attempt to place second order immediately
        result2 = executor.place_order(
            symbol=symbol,
            side='buy',
            price=price,
            size=size
        )
        
        self.assertFalse(result2.success)
        self.assertIn("Order interval too short", result2.error_message)
        
    def test_fill_handling(self):
        """Test order fill handling."""
        symbol = 'SOL/USD'
        price = Decimal('100')
        size = Decimal('0.5')
        
        # Place and fill buy order
        result = self.executor.place_order(
            symbol=symbol,
            side='buy',
            price=price,
            size=size
        )
        
        self.executor.handle_order_filled(
            order_id=result.order_id,
            filled_price=price,
            filled_quantity=size
        )
        
        # Verify position opened
        position = self.risk_manager.positions.get(symbol)
        self.assertIsNotNone(position)
        self.assertEqual(float(position.quantity), 0.5)
        self.assertEqual(float(position.entry_price), 100.0)
        
        # Place and fill sell order to close position
        result = self.executor.place_order(
            symbol=symbol,
            side='sell',
            price=Decimal('110'),
            size=size
        )
        
        self.executor.handle_order_filled(
            order_id=result.order_id,
            filled_price=Decimal('110'),
            filled_quantity=size
        )
        
        # Verify position closed and PnL recorded
        self.assertNotIn(symbol, self.risk_manager.positions)
        self.assertEqual(len(self.risk_manager.historical_trades), 1)
        trade = self.risk_manager.historical_trades[0]
        self.assertEqual(float(trade['pnl']), 5.0)  # (110 - 100) * 0.5
        
if __name__ == '__main__':
    unittest.main()
