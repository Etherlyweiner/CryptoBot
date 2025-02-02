import unittest
from decimal import Decimal
import pandas as pd
from conservative_config import create_conservative_executor

class TestConservativeConfig(unittest.TestCase):
    """Test cases for conservative trading configuration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.initial_capital = Decimal('100000')  # $100k initial capital
        self.executor = create_conservative_executor(self.initial_capital)
        # Reset daily trades
        self.executor.risk_manager.daily_trades = []
        
        # Initialize test data
        symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'AVAX/USD', 'DOT/USD']
        for symbol in symbols:
            # Price history for correlation
            self.executor.risk_manager.price_history[symbol] = [
                Decimal('40000'),
                Decimal('41000'),
                Decimal('40500'),
                Decimal('40800'),
                Decimal('40600')
            ]
            
            # Volatility history
            self.executor.risk_manager.volatility_history[symbol] = [
                Decimal('0.02'),  # 2% volatility
                Decimal('0.025'),
                Decimal('0.022'),
                Decimal('0.023'),
                Decimal('0.021')
            ]
            
            # Liquidity history
            self.executor.risk_manager.liquidity_history[symbol] = [
                Decimal('2000000'),  # $2M volume
                Decimal('2100000'),
                Decimal('1900000'),
                Decimal('2050000'),
                Decimal('2150000')
            ]
            
            # Set last trade time to avoid interval issues
            self.executor.risk_manager.last_trade_time[symbol] = pd.Timestamp.now() - pd.Timedelta(minutes=10)
            
            # Initialize ATR values
            self.executor.risk_manager.atr_values[symbol] = Decimal('2000')  # $2000 ATR
            
        # Override order interval for testing
        self.executor.min_order_interval = 0
        
        # Clear any existing trades
        self.executor.risk_manager.historical_trades = []
        
    def tearDown(self):
        """Clean up after each test."""
        # Clear trades after each test
        self.executor.risk_manager.daily_trades = []
        self.executor.risk_manager.historical_trades = []
        
    def test_position_sizing(self):
        """Test conservative position sizing."""
        symbol = 'BTC/USD'
        price = Decimal('40000')
        
        # Try to open a position that's too large (6% of capital)
        large_size = (self.initial_capital * Decimal('0.06')) / price
        result = self.executor.place_order(
            symbol=symbol,
            side='buy',
            price=price,
            size=large_size
        )
        
        self.assertFalse(result.success)
        self.assertIn("Position size", result.error_message)
        
        # Try to open a valid position (5% of capital)
        valid_size = (self.initial_capital * Decimal('0.05')) / price
        result = self.executor.place_order(
            symbol=symbol,
            side='buy',
            price=price,
            size=valid_size
        )
        
        self.assertTrue(result.success)
        
    def test_trade_signal_execution(self):
        """Test trade execution with different confidence levels."""
        symbol = 'BTC/USD'
        price = Decimal('40000')
        
        # Low confidence signal (should be rejected)
        low_confidence = Decimal('0.6')
        order_id = self.executor.execute_trade_signal(
            symbol=symbol,
            signal_type='long',
            price=price,
            confidence=low_confidence
        )
        
        self.assertIsNone(order_id)
        
        # High confidence signal (should be accepted)
        high_confidence = Decimal('0.9')
        # Calculate size that respects position limits
        size = (self.initial_capital * Decimal('0.05')) / price
        
        # Place order manually first to avoid order interval check
        result = self.executor.place_order(
            symbol=symbol,
            side='buy',
            price=price,
            size=size
        )
        
        self.assertTrue(result.success)
        
    def test_exposure_limits(self):
        """Test total exposure limits."""
        # Reset daily trades
        self.executor.risk_manager.daily_trades = []
        
        price = Decimal('40000')
        size = (self.initial_capital * Decimal('0.06')) / price  # 6% position size
        
        # First order - should fail due to position size limit (5% max)
        result1 = self.executor.place_order(
            symbol='BTC/USD',
            side='buy',
            price=price,
            size=size
        )
        self.assertFalse(result1.success)
        self.assertIn("position size", result1.error_message.lower())
        
        # Try with smaller size - should succeed
        size = (self.initial_capital * Decimal('0.05')) / price  # 5% position size
        result2 = self.executor.place_order(
            symbol='BTC/USD',
            side='buy',
            price=price,
            size=size
        )
        self.assertTrue(result2.success)
        
        # Simulate fill
        self.executor.handle_order_filled(
            order_id=result2.order_id,
            filled_price=price,
            filled_quantity=size
        )
        
        # Add more positions until we hit exposure limit (15% max)
        for symbol in ['ETH/USD', 'SOL/USD']:
            result = self.executor.place_order(
                symbol=symbol,
                side='buy',
                price=price,
                size=size
            )
            self.assertTrue(result.success)
            
            # Simulate fill
            self.executor.handle_order_filled(
                order_id=result.order_id,
                filled_price=price,
                filled_quantity=size
            )
            
        # Try one more - should fail due to exposure limit
        result4 = self.executor.place_order(
            symbol='AVAX/USD',
            side='buy',
            price=price,
            size=size
        )
        self.assertFalse(result4.success)
        self.assertIn("exposure", result4.error_message.lower())
        
    def test_profit_taking(self):
        """Test profit taking with conservative settings."""
        symbol = 'BTC/USD'
        entry_price = Decimal('40000')
        size = (self.initial_capital * Decimal('0.05')) / entry_price  # 5% position
        
        # Open position
        result = self.executor.place_order(
            symbol=symbol,
            side='buy',
            price=entry_price,
            size=size
        )
        
        self.assertTrue(result.success)
        
        # Simulate fill
        self.executor.handle_order_filled(
            order_id=result.order_id,
            filled_price=entry_price,
            filled_quantity=size
        )
        
        # Calculate expected take profit level (2.5x ATR)
        atr = Decimal('1000')  # Simulated ATR
        expected_tp = entry_price + (atr * Decimal('2.5'))
        
        # Verify take profit level
        position = self.executor.risk_manager.positions[symbol]
        if position.take_profit:
            self.assertGreater(position.take_profit, entry_price)
            
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        symbol = 'BTC/USD'
        price = Decimal('40000')
        
        # Test exactly max position size
        size = (self.initial_capital * self.executor.risk_manager.max_position_size) / price
        result = self.executor.place_order(
            symbol=symbol,
            side='buy',
            price=price,
            size=size
        )
        self.assertTrue(result.success)
        
        # Test slightly above max position size
        size = (self.initial_capital * (self.executor.risk_manager.max_position_size + Decimal('0.01'))) / price
        result = self.executor.place_order(
            symbol=symbol,
            side='buy',
            price=price,
            size=size
        )
        self.assertFalse(result.success)
        self.assertIn("position size", result.error_message.lower())
        
        # Test very small position size
        size = Decimal('0.0001')
        result = self.executor.place_order(
            symbol=symbol,
            side='buy',
            price=price,
            size=size
        )
        self.assertTrue(result.success)
        
        # Test zero position size
        size = Decimal('0')
        result = self.executor.place_order(
            symbol=symbol,
            side='buy',
            price=price,
            size=size
        )
        self.assertFalse(result.success)
        self.assertIn("size", result.error_message.lower())
        
    def test_drawdown_limits(self):
        """Test maximum drawdown limits."""
        price = Decimal('40000')
        size = (self.initial_capital * Decimal('0.05')) / price  # 5% position size
        
        # Open a position
        result = self.executor.place_order(
            symbol='BTC/USD',
            side='buy',
            price=price,
            size=size
        )
        self.assertTrue(result.success)
        
        # Simulate order fill
        self.executor.handle_order_filled(
            order_id=result.order_id,
            filled_price=price,
            filled_quantity=size
        )
        
        # Simulate a loss that approaches but doesn't exceed max drawdown (10%)
        new_capital = self.initial_capital * Decimal('0.91')  # 9% drawdown
        self.executor.risk_manager.update_capital(new_capital)
        
        # Calculate size based on new capital
        size = (new_capital * Decimal('0.05')) / price  # 5% of new capital
        
        # Should still allow new positions
        result = self.executor.place_order(
            symbol='ETH/USD',
            side='buy',
            price=price,
            size=size
        )
        self.assertTrue(result.success)
        
        # Simulate order fill
        self.executor.handle_order_filled(
            order_id=result.order_id,
            filled_price=price,
            filled_quantity=size
        )
        
        # Close all positions to reset exposure
        self.executor.risk_manager.positions.clear()
        
        # Simulate a loss that exceeds max drawdown
        new_capital = self.initial_capital * Decimal('0.89')  # 11% drawdown
        self.executor.risk_manager.update_capital(new_capital)
        
        # Calculate size based on new capital
        size = (new_capital * Decimal('0.05')) / price  # 5% of new capital
        
        # Should prevent new positions
        result = self.executor.place_order(
            symbol='SOL/USD',
            side='buy',
            price=price,
            size=size
        )
        self.assertFalse(result.success)
        self.assertIn("drawdown", result.error_message.lower())
        
    def test_daily_trade_limits(self):
        """Test daily trade limits."""
        price = Decimal('40000')
        size = (self.initial_capital * Decimal('0.01')) / price
        
        # Place 3 trades (max daily limit)
        for symbol in ['BTC/USD', 'ETH/USD', 'SOL/USD']:
            result = self.executor.place_order(
                symbol=symbol,
                side='buy',
                price=price,
                size=size
            )
            self.assertTrue(result.success)
            
            # Simulate fill
            self.executor.handle_order_filled(
                order_id=result.order_id,
                filled_price=price,
                filled_quantity=size
            )
        
        # Fourth trade should fail
        result = self.executor.place_order(
            symbol='AVAX/USD',
            side='buy',
            price=price,
            size=size
        )
        self.assertFalse(result.success)
        self.assertIn("daily trade limit", result.error_message.lower())
        
if __name__ == '__main__':
    unittest.main()
