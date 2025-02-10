"""Phantom wallet integration."""

import os
import logging
import tracemalloc
import asyncio
import aiohttp
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime
from solders.pubkey import Pubkey

logger = logging.getLogger(__name__)

# Enable tracemalloc for better debugging
tracemalloc.start()

class PhantomWalletManager:
    """Manager for Phantom wallet integration."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize wallet manager.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.wallet_config = config.get('wallet', {})
        self.address = self.wallet_config.get('address')
        self.session: Optional[aiohttp.ClientSession] = None
        self.connected = False
        
        # Initialize RPC endpoints with priority
        self.rpc_endpoints: List[str] = []
        network_config = config.get('network', {})
        
        # Add primary RPC endpoint
        if network_config.get('rpc_url'):
            logger.info("Added primary RPC endpoint")
            self.rpc_endpoints.append(network_config['rpc_url'])
            
        # Add backup endpoints
        backup_endpoints = network_config.get('backup_rpc_urls', [])
        for endpoint in backup_endpoints:
            logger.info(f"Added backup RPC endpoint: {endpoint}")
            self.rpc_endpoints.append(endpoint)
            
        if not self.rpc_endpoints:
            raise ValueError("No RPC endpoints configured")
            
        # Initialize connection settings
        self.connection_timeout = config.get('wallet', {}).get('connection_timeout_ms', 30000)
        self.auto_approve = config.get('wallet', {}).get('auto_approve_transactions', False)
        
    async def initialize(self):
        """Initialize wallet connection."""
        try:
            logger.info("Initializing Phantom wallet connection...")
            
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            if not self.address:
                logger.warning("No wallet address configured")
                return False
                
            # Test connection
            self.connected = await self.test_connection()
            if self.connected:
                logger.info(f"Connected to wallet: {self.address}")
            else:
                logger.error("Failed to connect to wallet")
                
            return self.connected
            
        except Exception as e:
            logger.error(f"Failed to initialize wallet: {str(e)}")
            return False
            
    async def test_connection(self) -> bool:
        """Test wallet connection.
        
        Returns:
            bool: True if connected
        """
        try:
            if not self.address:
                return False
                
            # Add actual connection test here
            return True
            
        except Exception as e:
            logger.error(f"Error testing wallet connection: {str(e)}")
            return False
            
    def is_connected(self) -> bool:
        """Check if wallet is connected.
        
        Returns:
            bool: True if connected
        """
        return self.connected
        
    async def get_balance(self) -> Optional[float]:
        """Get wallet balance.
        
        Returns:
            float: Balance in SOL or None if failed
        """
        try:
            if not self.connected:
                return None
                
            try:
                async with aiohttp.ClientSession() as session:
                    for endpoint in self.rpc_endpoints:
                        try:
                            async with session.post(
                                endpoint,
                                json={
                                    "jsonrpc": "2.0",
                                    "id": 1,
                                    "method": "getBalance",
                                    "params": [str(self.address)]
                                },
                                timeout=self.connection_timeout / 1000
                            ) as response:
                                if response.status == 200:
                                    data = await response.json()
                                    if 'result' in data:
                                        return data['result']['value'] / 1e9  # Convert lamports to SOL
                        except Exception as e:
                            logger.warning(f"Failed to get balance from {endpoint}: {str(e)}")
                            continue
                            
                logger.error("Failed to get balance from all RPC endpoints")
                return None
                
            except Exception as e:
                logger.error(f"Error getting wallet balance: {str(e)}")
                return None
            
        except Exception as e:
            logger.error(f"Error getting wallet balance: {str(e)}")
            return None
            
    async def close(self):
        """Close wallet connection."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
                
            self.connected = False
            logger.info("Closed wallet connection")
            
        except Exception as e:
            logger.error(f"Error closing wallet connection: {str(e)}")
            
    async def sign_transaction(self, transaction: Dict[str, Any]) -> Optional[str]:
        """Sign a transaction.
        
        Args:
            transaction: Transaction data
            
        Returns:
            str: Signed transaction or None if failed
        """
        try:
            if not self.connected:
                return None
                
            # This is a placeholder - actual implementation will depend on
            # how we integrate with Phantom's signing API
            logger.info("Transaction signing requested")
            return None
            
        except Exception as e:
            logger.error(f"Error signing transaction: {str(e)}")
            return None
