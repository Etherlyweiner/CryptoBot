"""
Test suite for risk management module.
"""

import unittest
from decimal import Decimal
import pandas as pd
import numpy as np
from risk_management import RiskManager, Position, RiskMetrics

class TestRiskManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.rm = RiskManager(
            initial_capital=Decimal('1000'),
            max_position_size=Decimal('0.1'),  # 10%
            max_total_exposure=Decimal('0.5'),  # 50%
            max_drawdown=Decimal('0.15'),  # 15%
            risk_per_trade=Decimal('0.02'),  # 2%
            atr_period=14,
            stop_loss_atr_multiplier=Decimal('1.0'),
            take_profit_atr_multiplier=Decimal('1.5')
        )
        
        # Create sample price data for ATR calculation
        self.prices = pd.DataFrame({
            'high': [110, 120, 115, 113, 118] * 3,
            'low': [90, 89, 85, 88, 92] * 3,
            'close': [100, 110, 90, 95, 105] * 3
        }, index=pd.date_range('2025-01-01', periods=15))
        
    def test_atr_calculation(self):
        """Test ATR calculation."""
        atr = self.rm.calculate_atr(self.prices['high'], self.prices['low'], self.prices['close'])
        self.assertIsInstance(atr, Decimal)
        self.assertGreater(float(atr), 0)
        
    def test_position_size_calculation(self):
        """Test position size calculation."""
        price = Decimal('100')
        stop_loss = Decimal('95')
        available_capital = self.rm.current_capital
        
        size = self.rm.calculate_position_size(price, stop_loss, available_capital)
        
        # Check that risk per trade is respected
        max_loss = float(abs(price - stop_loss) * size)
        self.assertLessEqual(max_loss, float(self.rm.current_capital * self.rm.risk_per_trade))
        
        # Check that position size respects max position size
        position_value = float(price * size)
        self.assertLessEqual(position_value, float(self.rm.current_capital * self.rm.max_position_size))
        
    def test_stop_loss_calculation(self):
        """Test stop loss calculation."""
        price = Decimal('100')
        atr = Decimal('5')
        
        # Test long position
        sl_long = self.rm.calculate_stop_loss(price, atr, 'long')
        self.assertLess(sl_long, price)
        self.assertEqual(float(price - sl_long), float(atr * self.rm.stop_loss_atr_multiplier))
        
        # Test short position
        sl_short = self.rm.calculate_stop_loss(price, atr, 'short')
        self.assertGreater(sl_short, price)
        self.assertEqual(float(sl_short - price), float(atr * self.rm.stop_loss_atr_multiplier))
        
    def test_take_profit_calculation(self):
        """Test take profit calculation."""
        price = Decimal('100')
        atr = Decimal('5')
        
        # Test long position
        tp_long = self.rm.calculate_take_profit(price, atr, 'long')
        self.assertGreater(tp_long, price)
        self.assertEqual(float(tp_long - price), float(atr * self.rm.take_profit_atr_multiplier))
        
        # Test short position
        tp_short = self.rm.calculate_take_profit(price, atr, 'short')
        self.assertLess(tp_short, price)
        self.assertEqual(float(price - tp_short), float(atr * self.rm.take_profit_atr_multiplier))
        
    def test_position_management(self):
        """Test position opening, updating, and closing."""
        symbol = 'SOL/USD'
        entry_price = Decimal('100')
        size = Decimal('0.5')  # Reduced size to respect position limits
        timestamp = pd.Timestamp('2025-01-01')
        
        # Open position
        position = self.rm.open_position(symbol, entry_price, size, 'long', timestamp)
        self.assertIsNotNone(position)
        self.assertEqual(position.symbol, symbol)
        self.assertEqual(position.entry_price, entry_price)
        self.assertEqual(position.quantity, size)
        
        # Update position - no trigger
        action = self.rm.update_position(symbol, Decimal('105'), timestamp)
        self.assertIsNone(action)
        
        # Close position
        exit_price = Decimal('110')
        trade_summary = self.rm.close_position(symbol, exit_price, timestamp)
        self.assertIsNotNone(trade_summary)
        self.assertEqual(float(trade_summary['pnl']), float((exit_price - entry_price) * size))
        
    def test_risk_metrics(self):
        """Test risk metrics calculation."""
        # Open a position
        symbol = 'SOL/USD'
        entry_price = Decimal('100')
        size = Decimal('0.5')  # Reduced size to respect position limits
        timestamp = pd.Timestamp('2025-01-01')
        
        self.rm.open_position(symbol, entry_price, size, 'long', timestamp)
        
        metrics = self.rm.get_risk_metrics()
        self.assertIsInstance(metrics, RiskMetrics)
        
        # Check exposure
        self.assertEqual(metrics.position_exposure[symbol], entry_price * size)
        self.assertEqual(metrics.total_exposure, entry_price * size)
        
        # Check risk per trade
        self.assertEqual(metrics.risk_per_trade, self.rm.risk_per_trade * metrics.total_value)
        
    def test_drawdown_protection(self):
        """Test drawdown protection."""
        symbol = 'SOL/USD'
        entry_price = Decimal('100')
        size = Decimal('0.5')  # Smaller position size to stay within limits
        timestamp = pd.Timestamp('2025-01-01')
        
        # Set initial capital and peak capital
        self.rm.current_capital = Decimal('1000')
        self.rm.peak_capital = Decimal('1000')
        
        # Open initial position
        position = self.rm.open_position(symbol, entry_price, size, 'long', timestamp)
        self.assertIsNotNone(position)
        
        # Simulate large loss exceeding max drawdown (15%)
        # Loss = 95% of position value (100 -> 5)
        # Position value = 50, Loss = 47.5
        # New capital = 1000 - 47.5 = 952.5
        # Drawdown = (1000 - 952.5) / 1000 = 0.0475 or 4.75%
        exit_price = Decimal('5')  # 95% loss
        trade = self.rm.close_position(symbol, exit_price, timestamp)
        self.assertIsNotNone(trade)
        self.assertEqual(float(trade['pnl']), -47.5)
        
        # Verify capital and drawdown
        self.assertEqual(float(self.rm.current_capital), 952.5)
        self.assertEqual(float(self.rm.peak_capital), 1000.0)
        
        # Calculate current drawdown
        current_drawdown = (self.rm.peak_capital - self.rm.current_capital) / self.rm.peak_capital
        
        # Open another position with larger size
        size = Decimal('0.8')  # Larger position to create bigger drawdown
        second_position = self.rm.open_position(symbol, entry_price, size, 'long', timestamp)
        self.assertIsNotNone(second_position)
        
        # Close with another big loss
        exit_price = Decimal('5')  # Another 95% loss
        trade = self.rm.close_position(symbol, exit_price, timestamp)
        self.assertIsNotNone(trade)
        self.assertEqual(float(trade['pnl']), -76.0)  # Loss of 95% of 80 value
        
        # Now our capital should be 876.5 (952.5 - 76)
        # Drawdown = (1000 - 876.5) / 1000 = 0.1235 or 12.35%
        self.assertEqual(float(self.rm.current_capital), 876.5)
        
        # Open third position with remaining capital
        size = Decimal('0.7')  # Another position to push drawdown over limit
        third_position = self.rm.open_position(symbol, entry_price, size, 'long', timestamp)
        self.assertIsNotNone(third_position)
        
        # Close with another big loss
        exit_price = Decimal('5')  # Another 95% loss
        trade = self.rm.close_position(symbol, exit_price, timestamp)
        self.assertIsNotNone(trade)
        self.assertEqual(float(trade['pnl']), -66.5)  # Loss of 95% of 70 value
        
        # Now our capital should be 810 (876.5 - 66.5)
        # Drawdown = (1000 - 810) / 1000 = 0.19 or 19%
        self.assertEqual(float(self.rm.current_capital), 810.0)
        
        # Calculate final drawdown
        final_drawdown = (self.rm.peak_capital - self.rm.current_capital) / self.rm.peak_capital
        self.assertGreater(float(final_drawdown), float(self.rm.max_drawdown))
        
        # Try to open new position - should fail due to drawdown
        new_symbol = 'ETH/USD'
        can_open, reason = self.rm.can_open_position(new_symbol, size, entry_price)
        self.assertFalse(can_open)
        self.assertIn("drawdown", reason.lower())
        
    def test_exposure_limits(self):
        """Test exposure limits."""
        symbol1 = 'SOL/USD'
        symbol2 = 'ETH/USD'
        price = Decimal('100')
        timestamp = pd.Timestamp('2025-01-01')
        
        # Set initial capital
        self.rm.current_capital = Decimal('1000')
        
        # Open first position at 9% exposure (90/1000)
        size1 = Decimal('0.9')  # 0.9 tokens * 100 price = 90 value (9%)
        position1 = self.rm.open_position(symbol1, price, size1, 'long', timestamp)
        self.assertIsNotNone(position1)
        
        # Verify first position exposure
        metrics = self.rm.get_risk_metrics()
        self.assertEqual(float(metrics.position_exposure[symbol1]), 90.0)  # 0.9 * 100
        
        # Try to open second position that would exceed max position size (10%)
        size2 = Decimal('1.1')  # 1.1 tokens * 100 price = 110 value (11%)
        can_open, reason = self.rm.can_open_position(symbol2, price, size2)
        self.assertFalse(can_open)
        self.assertIn("size", reason.lower())

if __name__ == '__main__':
    unittest.main()
