"""
Test suite for technical analysis module.
"""

import unittest
import pandas as pd
import numpy as np
from technical_analysis import TechnicalAnalysis, TradingSignal
from datetime import datetime, timedelta

class TestTechnicalAnalysis(unittest.TestCase):
    def setUp(self):
        """Set up test data."""
        # Create sample price data
        dates = pd.date_range(start='2025-01-01', periods=100, freq='h')
        # Generate synthetic price data with known patterns
        prices = []
        base_price = 100
        for i in range(100):
            # Add trend
            trend = i * 0.1
            # Add oscillation
            oscillation = 10 * np.sin(i * np.pi / 10)
            # Add some noise
            noise = np.random.normal(0, 1)
            price = base_price + trend + oscillation + noise
            prices.append(price)
        
        self.prices = pd.Series(prices, index=dates)
        self.ta = TechnicalAnalysis()
        
    def test_rsi_calculation(self):
        """Test RSI calculation."""
        rsi = self.ta.calculate_rsi(self.prices)
        
        # Check RSI bounds
        self.assertTrue(all(0 <= x <= 100 for x in rsi.dropna()))
        
        # Check RSI period
        self.assertEqual(len(rsi.dropna()), len(self.prices) - self.ta.rsi_period)
        
    def test_ema_calculation(self):
        """Test EMA calculation."""
        period = 10
        ema = self.ta.calculate_ema(self.prices, period)
        
        # Check EMA follows price direction
        price_diff = self.prices.diff().dropna()
        ema_diff = ema.diff().dropna()
        correlation = price_diff.corr(ema_diff)
        self.assertGreater(correlation, 0.5)
        
    def test_macd_calculation(self):
        """Test MACD calculation."""
        macd_line, signal_line, histogram = self.ta.calculate_macd(self.prices)
        
        # Check MACD components
        self.assertEqual(len(macd_line), len(self.prices))
        self.assertEqual(len(signal_line), len(self.prices))
        self.assertEqual(len(histogram), len(self.prices))
        
        # Verify histogram is difference of MACD and signal
        np.testing.assert_array_almost_equal(
            histogram.values,
            (macd_line - signal_line).values
        )
        
    def test_signal_generation(self):
        """Test trading signal generation."""
        signals = self.ta.generate_signals(self.prices)
        
        # Check that we have signals
        self.assertGreater(len(signals), 0)
        
        # Verify signal properties
        for signal in signals:
            # Check signal type
            self.assertIn(signal.signal_type, ['buy', 'sell'])
            
            # Check signal strength
            self.assertTrue(0 <= signal.strength <= 1)
            
            # Check indicator type
            self.assertIn(signal.indicator, ['RSI', 'MACD', 'EMA_CROSS'])
            
            # Check timestamp
            self.assertTrue(isinstance(signal.timestamp, pd.Timestamp))
            
            # Check price
            self.assertTrue(signal.price > 0)
            
    def test_signal_metadata(self):
        """Test signal metadata for each indicator type."""
        signals = self.ta.generate_signals(self.prices)
        
        for signal in signals:
            if signal.indicator == 'RSI':
                self.assertIn('rsi', signal.metadata)
                self.assertTrue(0 <= signal.metadata['rsi'] <= 100)
                
            elif signal.indicator == 'MACD':
                self.assertIn('macd', signal.metadata)
                self.assertIn('signal', signal.metadata)
                self.assertIn('histogram', signal.metadata)
                
            elif signal.indicator == 'EMA_CROSS':
                self.assertIn('ema_short', signal.metadata)
                self.assertIn('ema_long', signal.metadata)
                self.assertTrue(signal.metadata['ema_short'] > 0)
                self.assertTrue(signal.metadata['ema_long'] > 0)

if __name__ == '__main__':
    unittest.main()
