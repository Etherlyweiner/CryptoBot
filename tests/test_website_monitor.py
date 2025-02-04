"""
Unit tests for metrics collection
"""

import unittest
from unittest.mock import Mock
import time
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from cryptobot.monitoring.metrics import MetricsCollector

class TestMetricsCollection(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.metrics = MetricsCollector()
        
    def test_singleton_pattern(self):
        """Test that MetricsCollector follows singleton pattern"""
        metrics2 = MetricsCollector()
        self.assertIs(self.metrics, metrics2)
    
    def test_trade_metrics(self):
        """Test trade metrics collection"""
        # Record a trade
        self.metrics.record_trade(100.0, 0.5)  # 100 SOL trade taking 0.5 seconds
        
        # Get metrics and verify
        metrics = self.metrics.get_metrics()
        self.assertGreater(metrics['trades']['total_executed'], 0)
        self.assertGreater(metrics['trades']['total_volume'], 0)
    
    def test_error_metrics(self):
        """Test error metrics collection"""
        # Record an error
        self.metrics.record_error("TEST_ERROR")
        
        # Get metrics and verify
        metrics = self.metrics.get_metrics()
        self.assertGreater(metrics['errors']['total'], 0)
    
    def test_performance_metrics(self):
        """Test performance metrics collection"""
        # Record RPC request
        start_time = time.time() - 0.5  # Simulate request that started 0.5 seconds ago
        self.metrics.record_rpc_request(start_time)
        
        # Get metrics and verify
        metrics = self.metrics.get_metrics()
        self.assertGreater(metrics['performance']['avg_rpc_latency'], 0)
    
    def test_portfolio_metrics(self):
        """Test portfolio metrics collection"""
        # Update portfolio
        self.metrics.update_portfolio(1000.0, 5)  # 1000 SOL portfolio with 5 positions
        
        # Get metrics and verify
        metrics = self.metrics.get_metrics()
        self.assertEqual(metrics['trades']['portfolio_value'], 1000.0)
        self.assertEqual(metrics['trades']['active_positions'], 5)

if __name__ == '__main__':
    unittest.main()
