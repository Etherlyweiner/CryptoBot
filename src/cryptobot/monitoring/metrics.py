"""
Metrics Collection for CryptoBot
"""

import time
from typing import Dict, Optional
from prometheus_client import Counter, Gauge, Histogram, REGISTRY
import threading

class MetricsCollector:
    """Singleton metrics collector for the trading bot."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize metrics collector."""
        if hasattr(self, '_initialized'):
            return
            
        # Create custom registry
        self.registry = REGISTRY
        
        # Trading metrics
        self.trades_executed = Counter(
            'cryptobot_trades_executed_total',
            'Total number of trades executed',
            registry=self.registry
        )
        
        self.trade_volume = Counter(
            'cryptobot_trade_volume_sol',
            'Total trading volume in SOL',
            registry=self.registry
        )
        
        self.active_positions = Gauge(
            'cryptobot_active_positions',
            'Number of currently active positions',
            registry=self.registry
        )
        
        self.portfolio_value = Gauge(
            'cryptobot_portfolio_value_sol',
            'Current portfolio value in SOL',
            registry=self.registry
        )
        
        # Performance metrics
        self.trade_execution_time = Histogram(
            'cryptobot_trade_execution_seconds',
            'Time taken to execute trades',
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0),
            registry=self.registry
        )
        
        self.rpc_latency = Histogram(
            'cryptobot_rpc_latency_seconds',
            'RPC request latency',
            buckets=(0.05, 0.1, 0.2, 0.5, 1.0),
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'cryptobot_errors_total',
            'Total number of errors',
            ['type'],
            registry=self.registry
        )
        
        self.failed_trades = Counter(
            'cryptobot_failed_trades_total',
            'Total number of failed trades',
            ['reason'],
            registry=self.registry
        )
        
        self._initialized = True
    
    def record_trade(self, volume: float, execution_time: float):
        """Record a successful trade."""
        self.trades_executed.inc()
        self.trade_volume.inc(volume)
        self.trade_execution_time.observe(execution_time)
    
    def update_portfolio(self, value: float, positions: int):
        """Update portfolio metrics."""
        self.portfolio_value.set(value)
        self.active_positions.set(positions)
    
    def record_rpc_request(self, start_time: float):
        """Record RPC request latency."""
        latency = time.time() - start_time
        self.rpc_latency.observe(latency)
    
    def record_error(self, error_type: str, details: Optional[Dict] = None):
        """Record an error."""
        self.errors_total.labels(type=error_type).inc()
        
        if error_type == 'trade_failure' and details:
            self.failed_trades.labels(reason=details.get('reason', 'unknown')).inc()
    
    def get_metrics(self) -> Dict:
        """Get current metrics as a dictionary."""
        return {
            'trades': {
                'total_executed': float(self.trades_executed._value.get()),
                'total_volume': float(self.trade_volume._value.get()),
                'active_positions': float(self.active_positions._value.get()),
                'portfolio_value': float(self.portfolio_value._value.get())
            },
            'performance': {
                'avg_execution_time': float(self.trade_execution_time._sum.get()),
                'avg_rpc_latency': float(self.rpc_latency._sum.get())
            },
            'errors': {
                'total': sum(self.errors_total._metrics.values()),
                'failed_trades': sum(self.failed_trades._metrics.values())
            }
        }
