"""
Queue-based trade processor with rate limiting and circuit breaker.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import deque
import aioredis
from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)

# Prometheus metrics
QUEUE_SIZE = Gauge('trade_queue_size', 'Number of trades in queue')
PROCESSED_TRADES = Counter('processed_trades_total', 'Total number of processed trades')
FAILED_TRADES = Counter('failed_trades_total', 'Total number of failed trades')
CIRCUIT_BREAKS = Counter('circuit_breaker_trips', 'Number of times circuit breaker was triggered')

@dataclass
class CircuitBreaker:
    """Circuit breaker for trade processing."""
    failure_threshold: int = 5
    reset_timeout: int = 60  # seconds
    failures: int = 0
    last_failure_time: Optional[datetime] = None
    is_open: bool = False

    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        current_time = datetime.utcnow()
        if (self.last_failure_time and 
            (current_time - self.last_failure_time) > timedelta(seconds=self.reset_timeout)):
            self.failures = 0
        
        self.failures += 1
        self.last_failure_time = current_time
        
        if self.failures >= self.failure_threshold:
            self.is_open = True
            CIRCUIT_BREAKS.inc()
            logger.warning("Circuit breaker opened due to multiple failures")

    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if not self.is_open:
            return True
            
        if (datetime.utcnow() - self.last_failure_time) > timedelta(seconds=self.reset_timeout):
            self.is_open = False
            self.failures = 0
            logger.info("Circuit breaker reset after timeout")
            return True
            
        return False

class RateLimiter:
    """Rate limiter using token bucket algorithm."""
    def __init__(self, rate: int, burst: int):
        self.rate = rate  # tokens per second
        self.burst = burst
        self.tokens = burst
        self.last_update = asyncio.get_event_loop().time()
        self.lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Acquire a token if available."""
        async with self.lock:
            now = asyncio.get_event_loop().time()
            time_passed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + time_passed * self.rate)
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False

class TradeProcessor:
    """Asynchronous trade processor with queue management."""
    def __init__(self, redis_url: str = "redis://localhost"):
        self.queue = asyncio.Queue()
        self.circuit_breaker = CircuitBreaker()
        self.rate_limiter = RateLimiter(rate=10, burst=20)  # 10 trades per second, burst of 20
        self.redis = None
        self.redis_url = redis_url
        self.processing = False
        self.handlers: Dict[str, Callable] = {}

    async def connect(self):
        """Connect to Redis for distributed processing."""
        self.redis = await aioredis.from_url(self.redis_url)
        logger.info("Connected to Redis for distributed processing")

    async def enqueue_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Add trade to processing queue."""
        if not self.circuit_breaker.can_execute():
            logger.warning("Circuit breaker is open, rejecting trade")
            return False

        await self.queue.put(trade_data)
        QUEUE_SIZE.inc()
        logger.info(f"Trade enqueued. Queue size: {self.queue.qsize()}")
        return True

    async def process_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Process a single trade with rate limiting."""
        try:
            if not await self.rate_limiter.acquire():
                logger.warning("Rate limit exceeded, delaying trade")
                await asyncio.sleep(0.1)
                return False

            # Execute registered handlers
            for handler_name, handler_func in self.handlers.items():
                try:
                    await handler_func(trade_data)
                except Exception as e:
                    logger.error(f"Handler {handler_name} failed: {str(e)}")
                    return False

            PROCESSED_TRADES.inc()
            return True

        except Exception as e:
            logger.error(f"Trade processing failed: {str(e)}")
            FAILED_TRADES.inc()
            self.circuit_breaker.record_failure()
            return False

    async def start_processing(self):
        """Start processing trades from queue."""
        self.processing = True
        await self.connect()
        
        while self.processing:
            try:
                trade_data = await self.queue.get()
                QUEUE_SIZE.dec()
                
                success = await self.process_trade(trade_data)
                if not success and self.processing:
                    # Re-queue failed trades with exponential backoff
                    await asyncio.sleep(1)
                    await self.enqueue_trade(trade_data)
                
                self.queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in trade processor: {str(e)}")
                await asyncio.sleep(1)

    def register_handler(self, name: str, handler: Callable):
        """Register a trade processing handler."""
        self.handlers[name] = handler
        logger.info(f"Registered trade handler: {name}")

    async def stop(self):
        """Stop the trade processor."""
        self.processing = False
        if self.redis:
            await self.redis.close()
        logger.info("Trade processor stopped")
