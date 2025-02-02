"""Load balancer for distributing API requests across endpoints."""

import asyncio
import logging
import random
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import aiohttp
from dataclasses import dataclass
from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger('LoadBalancer')

@dataclass
class Endpoint:
    """API endpoint information."""
    url: str
    weight: int = 1
    health_score: float = 1.0
    last_check: Optional[datetime] = None
    error_count: int = 0
    latency_ms: float = 0.0
    is_active: bool = True

class LoadBalancer:
    """Load balancer for API endpoints."""
    
    def __init__(self,
                 endpoints: List[str],
                 check_interval: int = 60,
                 max_retries: int = 3,
                 timeout: float = 10.0):
        """Initialize load balancer."""
        self.endpoints = {
            url: Endpoint(url=url)
            for url in endpoints
        }
        self.check_interval = check_interval
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Session pool
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        )
        
        # Prometheus metrics
        self.request_count = Counter(
            'api_requests_total',
            'Total number of API requests',
            ['endpoint']
        )
        self.error_count = Counter(
            'api_errors_total',
            'Total number of API errors',
            ['endpoint', 'error_type']
        )
        self.latency = Histogram(
            'api_request_duration_seconds',
            'API request latency',
            ['endpoint']
        )
        self.health_score = Gauge(
            'endpoint_health_score',
            'Health score of endpoints',
            ['endpoint']
        )
        
        # Start health checks
        asyncio.create_task(self._health_check_loop())
        
    async def _health_check_loop(self):
        """Continuously check endpoint health."""
        while True:
            try:
                await self._check_all_endpoints()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(self.check_interval)
                
    async def _check_endpoint(self, endpoint: Endpoint):
        """Check health of a single endpoint."""
        try:
            start_time = datetime.now()
            async with self.session.get(
                f"{endpoint.url}/health",
                timeout=self.timeout
            ) as response:
                latency = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    endpoint.latency_ms = latency
                    endpoint.error_count = max(0, endpoint.error_count - 1)
                    endpoint.is_active = True
                else:
                    endpoint.error_count += 1
                    
                # Update health score based on latency and errors
                endpoint.health_score = self._calculate_health_score(endpoint)
                endpoint.last_check = datetime.now()
                
                # Update metrics
                self.health_score.labels(endpoint=endpoint.url).set(
                    endpoint.health_score
                )
                
        except Exception as e:
            logger.error(f"Health check failed for {endpoint.url}: {e}")
            endpoint.error_count += 1
            endpoint.health_score = self._calculate_health_score(endpoint)
            endpoint.last_check = datetime.now()
            
            if endpoint.error_count >= self.max_retries:
                endpoint.is_active = False
                logger.warning(f"Endpoint {endpoint.url} marked as inactive")
                
    async def _check_all_endpoints(self):
        """Check health of all endpoints."""
        tasks = [
            self._check_endpoint(endpoint)
            for endpoint in self.endpoints.values()
        ]
        await asyncio.gather(*tasks)
        
    def _calculate_health_score(self, endpoint: Endpoint) -> float:
        """Calculate health score for an endpoint."""
        if not endpoint.is_active:
            return 0.0
            
        # Base score affected by error count
        error_factor = max(0, 1 - (endpoint.error_count * 0.2))
        
        # Latency factor (assuming 1000ms as high latency)
        latency_factor = max(0, 1 - (endpoint.latency_ms / 1000))
        
        # Combine factors
        health_score = (error_factor * 0.6) + (latency_factor * 0.4)
        return max(0, min(1, health_score))
        
    def _select_endpoint(self) -> Optional[Endpoint]:
        """Select best endpoint based on health scores."""
        active_endpoints = [
            endpoint for endpoint in self.endpoints.values()
            if endpoint.is_active
        ]
        
        if not active_endpoints:
            return None
            
        # Weight selection by health score
        total_health = sum(e.health_score for e in active_endpoints)
        if total_health <= 0:
            return random.choice(active_endpoints)
            
        r = random.uniform(0, total_health)
        cumulative = 0
        
        for endpoint in active_endpoints:
            cumulative += endpoint.health_score
            if cumulative >= r:
                return endpoint
                
        return active_endpoints[-1]
        
    async def request(self,
                     method: str,
                     path: str,
                     **kwargs) -> Any:
        """Make a load-balanced API request."""
        for attempt in range(self.max_retries):
            endpoint = self._select_endpoint()
            if not endpoint:
                raise RuntimeError("No active endpoints available")
                
            url = f"{endpoint.url}{path}"
            
            try:
                start_time = datetime.now()
                async with self.session.request(
                    method,
                    url,
                    **kwargs
                ) as response:
                    latency = (datetime.now() - start_time).total_seconds()
                    
                    # Update metrics
                    self.request_count.labels(endpoint=endpoint.url).inc()
                    self.latency.labels(endpoint=endpoint.url).observe(latency)
                    
                    if response.status >= 500:
                        self.error_count.labels(
                            endpoint=endpoint.url,
                            error_type='server_error'
                        ).inc()
                        continue
                        
                    if response.status == 429:
                        self.error_count.labels(
                            endpoint=endpoint.url,
                            error_type='rate_limit'
                        ).inc()
                        retry_after = int(response.headers.get('Retry-After', 5))
                        await asyncio.sleep(retry_after)
                        continue
                        
                    if response.status >= 400:
                        self.error_count.labels(
                            endpoint=endpoint.url,
                            error_type='client_error'
                        ).inc()
                        response.raise_for_status()
                        
                    return await response.json()
                    
            except Exception as e:
                logger.error(f"Request to {url} failed: {e}")
                self.error_count.labels(
                    endpoint=endpoint.url,
                    error_type='connection_error'
                ).inc()
                
                if attempt == self.max_retries - 1:
                    raise
                    
        raise RuntimeError("Max retries exceeded")
        
    async def close(self):
        """Clean up resources."""
        await self.session.close()
        
# Example usage:
# load_balancer = LoadBalancer([
#     'https://api1.example.com',
#     'https://api2.example.com',
#     'https://api3.example.com'
# ])
