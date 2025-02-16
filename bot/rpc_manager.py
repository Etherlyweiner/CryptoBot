"""RPC manager for handling Solana network connections."""

import logging
from typing import Dict, Any, Optional
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment

from .helius_client import HeliusClient

logger = logging.getLogger(__name__)

class RPCManager:
    """Manages RPC connections to the Solana network."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize RPC manager."""
        self.config = config
        self.helius = HeliusClient(config)
        self.initialized = False
        
    async def initialize(self):
        """Initialize RPC connections."""
        try:
            if self.initialized:
                return
                
            logger.info("Initializing RPC manager...")
            
            # Initialize Helius client
            await self.helius.initialize()
            
            self.initialized = True
            logger.info("RPC manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RPC manager: {str(e)}")
            await self.cleanup()
            raise
            
    async def cleanup(self):
        """Clean up RPC connections."""
        try:
            await self.helius.cleanup()
            self.initialized = False
        except Exception as e:
            logger.error(f"Error cleaning up RPC connections: {str(e)}")
            raise
            
    @property
    def client(self) -> AsyncClient:
        """Get the primary RPC client."""
        if not self.initialized or not self.helius.client:
            raise Exception("RPC manager not initialized")
        return self.helius.client
        
    async def get_token_balance(self, token_account: str) -> Optional[Dict[str, Any]]:
        """Get token balance for a specific token account."""
        try:
            response = await self.client.get_token_account_balance(token_account)
            return response
        except Exception as e:
            logger.error(f"Failed to get token balance: {str(e)}")
            return None
            
    async def get_token_metadata(self, mint_address: str) -> Optional[Dict[str, Any]]:
        """Get token metadata."""
        try:
            return await self.helius.get_token_metadata(mint_address)
        except Exception as e:
            logger.error(f"Failed to get token metadata: {str(e)}")
            return None
            
    async def get_transaction_history(self, address: str, limit: int = 100) -> Optional[Dict[str, Any]]:
        """Get transaction history for an address."""
        try:
            return await self.helius.get_transaction_history(address, limit)
        except Exception as e:
            logger.error(f"Failed to get transaction history: {str(e)}")
            return None
            
    async def get_token_holders(self, mint_address: str) -> Optional[Dict[str, Any]]:
        """Get token holders for a mint."""
        try:
            return await self.helius.get_token_holders(mint_address)
        except Exception as e:
            logger.error(f"Failed to get token holders: {str(e)}")
            return None
            
    async def get_token_balances(self, owner_address: str) -> Optional[Dict[str, Any]]:
        """Get all token balances for an owner."""
        try:
            return await self.helius.get_token_balances(owner_address)
        except Exception as e:
            logger.error(f"Failed to get token balances: {str(e)}")
            return None
