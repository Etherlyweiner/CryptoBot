"""Prometheus metrics collection for CryptoBot."""

from prometheus_client import Counter, Gauge, Histogram, start_http_server, CollectorRegistry
import time
from typing import Dict, Optional
from decimal import Decimal
import logging
from functools import wraps

logger = logging.getLogger('MetricsCollector')

class MetricsCollector:
    """Collects and exposes Prometheus metrics."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, port: int = 9090):
        """Initialize metrics collector."""
        if self._initialized:
            return
            
        # Create a new registry
        self.registry = CollectorRegistry()
        
        # Trading metrics
        self.trade_count = Counter(
            'cryptobot_trades_total',
            'Total number of trades',
            ['symbol', 'side', 'result'],
            registry=self.registry
        )
        
        self.position_size = Gauge(
            'cryptobot_position_size',
            'Current position size',
            ['symbol'],
            registry=self.registry
        )
        
        self.position_value = Gauge(
            'cryptobot_position_value',
            'Current position value in quote currency',
            ['symbol'],
            registry=self.registry
        )
        
        self.pnl = Counter(
            'cryptobot_pnl_total',
            'Total profit and loss',
            ['symbol'],
            registry=self.registry
        )
        
        self.total_exposure = Gauge(
            'cryptobot_total_exposure',
            'Total trading exposure',
            registry=self.registry
        )
        
        self.current_drawdown = Gauge(
            'cryptobot_current_drawdown',
            'Current drawdown percentage',
            registry=self.registry
        )
        
        self.profit_loss = Counter(
            'cryptobot_profit_loss_total',
            'Total profit/loss',
            ['symbol'],
            registry=self.registry
        )
        
        # Performance metrics
        self.api_latency = Histogram(
            'cryptobot_api_latency_seconds',
            'API request latency',
            ['endpoint'],
            registry=self.registry
        )
        
        self.order_execution_time = Histogram(
            'cryptobot_order_execution_seconds',
            'Order execution time',
            ['symbol', 'side'],
            registry=self.registry
        )
        
        # System metrics
        self.memory_usage = Gauge(
            'cryptobot_memory_bytes',
            'Memory usage in bytes',
            registry=self.registry
        )
        
        self.cpu_usage = Gauge(
            'cryptobot_cpu_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        self.db_connections = Gauge(
            'cryptobot_db_connections',
            'Number of active database connections',
            registry=self.registry
        )
        
        # Error metrics
        self.error_count = Counter(
            'cryptobot_errors_total',
            'Total number of errors',
            ['type'],
            registry=self.registry
        )
        
        # Start metrics server with our registry
        start_http_server(port, registry=self.registry)
        logger.info(f"Metrics server started on port {port}")
        
        self._initialized = True
        
    def track_trade(self,
                   symbol: str,
                   side: str,
                   size: Decimal,
                   profit_loss: Optional[Decimal] = None) -> None:
        """Track trade execution."""
        result = 'profit' if profit_loss and profit_loss > 0 else 'loss'
        self.trade_count.labels(symbol=symbol, side=side, result=result).inc()
        
        if profit_loss:
            self.profit_loss.labels(symbol=symbol).inc(float(profit_loss))
            
        self.position_size.labels(symbol=symbol).set(float(size))
        
    def update_risk_metrics(self,
                          total_exposure: Decimal,
                          drawdown: Decimal) -> None:
        """Update risk-related metrics."""
        self.total_exposure.set(float(total_exposure))
        self.current_drawdown.set(float(drawdown))
        
    def track_api_call(self, endpoint: str) -> callable:
        """Decorator to track API latency."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    self.api_latency.labels(endpoint=endpoint).observe(
                        time.time() - start_time
                    )
                    return result
                except Exception as e:
                    self.error_count.labels(type=type(e).__name__).inc()
                    raise
            return wrapper
        return decorator
        
    def track_order_execution(self, symbol: str, side: str) -> callable:
        """Decorator to track order execution time."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    self.order_execution_time.labels(
                        symbol=symbol,
                        side=side
                    ).observe(time.time() - start_time)
                    return result
                except Exception as e:
                    self.error_count.labels(type=type(e).__name__).inc()
                    raise
            return wrapper
        return decorator
        
    def update_system_metrics(self,
                            memory_bytes: int,
                            cpu_percent: float,
                            db_connections: int) -> None:
        """Update system metrics."""
        self.memory_usage.set(memory_bytes)
        self.cpu_usage.set(cpu_percent)
        self.db_connections.set(db_connections)
        
# Global metrics collector instance
metrics = MetricsCollector()
