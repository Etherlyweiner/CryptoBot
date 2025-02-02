"""
HTTP Server module for serving the CryptoBot web interface.
"""

from typing import Optional, Type, Dict, Any
import http.server
import socketserver
import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from prometheus_client import Counter, start_http_server
from aiohttp import web
from .trade_processor import TradeProcessor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests')
TRADE_REQUEST_COUNT = Counter('trade_requests_total', 'Total trade requests')

class LoadBalancer:
    """Simple round-robin load balancer."""
    def __init__(self):
        self.servers = []
        self.current = 0
        self.lock = asyncio.Lock()

    def add_server(self, server: str):
        """Add a server to the load balancer."""
        self.servers.append(server)

    async def get_next_server(self) -> Optional[str]:
        """Get the next server in round-robin fashion."""
        async with self.lock:
            if not self.servers:
                return None
            server = self.servers[self.current]
            self.current = (self.current + 1) % len(self.servers)
            return server

class CryptoBotServer:
    """Enhanced HTTP server with WebSocket support and load balancing."""
    def __init__(self):
        self.app = web.Application()
        self.trade_processor = TradeProcessor()
        self.load_balancer = LoadBalancer()
        self.setup_routes()

    def setup_routes(self):
        """Set up HTTP routes."""
        self.app.router.add_post('/api/trade', self.handle_trade)
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_static('/', path=str(get_static_dir()))

    async def handle_trade(self, request: web.Request) -> web.Response:
        """Handle incoming trade requests."""
        try:
            TRADE_REQUEST_COUNT.inc()
            data = await request.json()
            
            # Validate trade data
            if not self.validate_trade_data(data):
                return web.Response(
                    status=400,
                    text=json.dumps({"error": "Invalid trade data"})
                )

            # Get next available server
            server = await self.load_balancer.get_next_server()
            if not server:
                return web.Response(
                    status=503,
                    text=json.dumps({"error": "No available servers"})
                )

            # Enqueue trade for processing
            success = await self.trade_processor.enqueue_trade(data)
            if not success:
                return web.Response(
                    status=429,
                    text=json.dumps({"error": "Trade processing temporarily unavailable"})
                )

            return web.Response(
                status=202,
                text=json.dumps({"message": "Trade accepted for processing"})
            )

        except Exception as e:
            logger.error(f"Error processing trade request: {str(e)}")
            return web.Response(
                status=500,
                text=json.dumps({"error": "Internal server error"})
            )

    async def handle_status(self, request: web.Request) -> web.Response:
        """Handle status check requests."""
        REQUEST_COUNT.inc()
        return web.Response(
            text=json.dumps({
                "status": "healthy",
                "queue_size": self.trade_processor.queue.qsize(),
                "circuit_breaker": not self.trade_processor.circuit_breaker.is_open
            })
        )

    @staticmethod
    def validate_trade_data(data: Dict[str, Any]) -> bool:
        """Validate incoming trade data."""
        required_fields = ['token_address', 'amount', 'type']
        return all(field in data for field in required_fields)

def get_static_dir() -> Path:
    """Get the absolute path to the static directory."""
    return Path(__file__).parent.parent / 'static'

async def run_server(
    hostname: str = "localhost",
    port: int = 8080,
    metrics_port: int = 8081
) -> None:
    """
    Run the HTTP server with metrics endpoint.
    
    Args:
        hostname: The hostname to bind to
        port: The port to listen on
        metrics_port: Port for Prometheus metrics
    """
    try:
        # Start Prometheus metrics server
        start_http_server(metrics_port)
        logger.info(f"Metrics server started on port {metrics_port}")

        # Create and configure the server
        server = CryptoBotServer()
        
        # Add some example backend servers (in production, this would be dynamic)
        server.load_balancer.add_server("server1:8080")
        server.load_balancer.add_server("server2:8080")

        # Start the trade processor
        asyncio.create_task(server.trade_processor.start_processing())
        
        # Start the main server
        runner = web.AppRunner(server.app)
        await runner.setup()
        site = web.TCPSite(runner, hostname, port)
        
        logger.info(f"Starting server on {hostname}:{port}")
        await site.start()
        
        # Keep the server running
        while True:
            await asyncio.sleep(3600)

    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(run_server())
