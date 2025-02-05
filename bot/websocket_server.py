"""WebSocket server for real-time updates."""

import asyncio
import json
import logging
from typing import Dict, Set, Any
import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)

class WebSocketServer:
    """WebSocket server for real-time updates."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        """Initialize WebSocket server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
        """
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None
        
    async def start(self):
        """Start the WebSocket server."""
        try:
            self.server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port
            )
            logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {str(e)}")
            raise
            
    async def stop(self):
        """Stop the WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")
            
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a client connection.
        
        Args:
            websocket: WebSocket connection
            path: Connection path
        """
        try:
            # Register client
            self.clients.add(websocket)
            logger.info(f"Client connected from {websocket.remote_address}")
            
            try:
                async for message in websocket:
                    try:
                        # Parse client message
                        data = json.loads(message)
                        msg_type = data.get('type')
                        
                        if msg_type == 'ping':
                            await websocket.send(json.dumps({
                                'type': 'pong',
                                'timestamp': data.get('timestamp')
                            }))
                            
                        elif msg_type == 'subscribe':
                            # Handle subscription requests
                            topics = data.get('topics', [])
                            if topics:
                                logger.info(f"Client subscribed to topics: {topics}")
                                
                        else:
                            logger.warning(f"Unknown message type: {msg_type}")
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON message: {message}")
                        
                    except Exception as e:
                        logger.error(f"Error handling message: {str(e)}")
                        
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"Client connection closed normally")
                
            except Exception as e:
                logger.error(f"Client connection error: {str(e)}")
                
        finally:
            # Unregister client
            self.clients.remove(websocket)
            logger.info(f"Client disconnected from {websocket.remote_address}")
            
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients.
        
        Args:
            message: Message to broadcast
        """
        if not self.clients:
            return
            
        # Prepare message
        try:
            message_str = json.dumps(message)
        except Exception as e:
            logger.error(f"Failed to serialize message: {str(e)}")
            return
            
        # Send to all clients
        disconnected_clients = set()
        for client in self.clients:
            try:
                await client.send(message_str)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Failed to send message to client: {str(e)}")
                disconnected_clients.add(client)
                
        # Remove disconnected clients
        for client in disconnected_clients:
            self.clients.remove(client)
            
    async def broadcast_update(self, update_type: str, data: Dict[str, Any]):
        """Broadcast an update message.
        
        Args:
            update_type: Type of update
            data: Update data
        """
        await self.broadcast({
            'type': update_type,
            'data': data
        })
