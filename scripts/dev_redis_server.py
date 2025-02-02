"""
Lightweight Redis-like server for development.
"""
import asyncio
import json
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import pickle
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DevRedisServer:
    def __init__(self, host='localhost', port=6380):
        self.host = host
        self.port = port
        self.data: Dict[str, Any] = {}
        self.expires: Dict[str, float] = {}
        self.save_interval = 300  # 5 minutes
        self.data_file = Path("data/redis_data.pkl")
        self.data_file.parent.mkdir(exist_ok=True)
        
        # Load existing data
        self._load_data()
        
        # Start save thread
        self.running = True
        self.save_thread = threading.Thread(target=self._periodic_save)
        self.save_thread.daemon = True
        self.save_thread.start()
    
    def _load_data(self):
        """Load data from disk if exists."""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'rb') as f:
                    saved_data = pickle.load(f)
                    self.data = saved_data.get('data', {})
                    self.expires = saved_data.get('expires', {})
                    
                    # Clean up expired keys
                    now = time.time()
                    expired = [
                        k for k, v in self.expires.items()
                        if v <= now
                    ]
                    for k in expired:
                        self.data.pop(k, None)
                        self.expires.pop(k, None)
                    
                logger.info("Loaded existing data from disk")
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
    
    def _save_data(self):
        """Save data to disk."""
        try:
            with open(self.data_file, 'wb') as f:
                pickle.dump({
                    'data': self.data,
                    'expires': self.expires
                }, f)
            logger.info("Saved data to disk")
        except Exception as e:
            logger.error(f"Error saving data: {str(e)}")
    
    def _periodic_save(self):
        """Periodically save data to disk."""
        while self.running:
            time.sleep(self.save_interval)
            self._save_data()
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client connection."""
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                
                try:
                    request = json.loads(data.decode())
                    command = request.get('command')
                    args = request.get('args', [])
                    
                    if command == 'ping':
                        response = {'status': 'ok', 'data': 'PONG'}
                    
                    elif command == 'set':
                        key, value = args[:2]
                        ttl = args[2] if len(args) > 2 else None
                        self.data[key] = value
                        if ttl:
                            self.expires[key] = time.time() + ttl
                        response = {'status': 'ok'}
                    
                    elif command == 'get':
                        key = args[0]
                        if key in self.expires and time.time() > self.expires[key]:
                            self.data.pop(key, None)
                            self.expires.pop(key, None)
                            response = {'status': 'ok', 'data': None}
                        else:
                            response = {'status': 'ok', 'data': self.data.get(key)}
                    
                    elif command == 'delete':
                        key = args[0]
                        self.data.pop(key, None)
                        self.expires.pop(key, None)
                        response = {'status': 'ok'}
                    
                    elif command == 'hset':
                        key, field, value = args
                        if key not in self.data:
                            self.data[key] = {}
                        self.data[key][field] = value
                        response = {'status': 'ok'}
                    
                    elif command == 'hget':
                        key, field = args
                        response = {
                            'status': 'ok',
                            'data': self.data.get(key, {}).get(field)
                        }
                    
                    else:
                        response = {
                            'status': 'error',
                            'message': f'Unknown command: {command}'
                        }
                    
                    writer.write(json.dumps(response).encode())
                    await writer.drain()
                    
                except json.JSONDecodeError:
                    writer.write(json.dumps({
                        'status': 'error',
                        'message': 'Invalid JSON'
                    }).encode())
                    await writer.drain()
                
        except Exception as e:
            logger.error(f"Error handling client: {str(e)}")
        finally:
            writer.close()
            await writer.wait_closed()
    
    async def start(self):
        """Start the server."""
        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        
        logger.info(f"Server running on {self.host}:{self.port}")
        
        async with server:
            await server.serve_forever()
    
    def stop(self):
        """Stop the server."""
        self.running = False
        self._save_data()
        logger.info("Server stopped")

async def main():
    """Run the server."""
    server = DevRedisServer()
    try:
        await server.start()
    except KeyboardInterrupt:
        server.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
