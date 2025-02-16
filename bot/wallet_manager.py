"""Wallet manager for handling Solana wallets and transactions."""

import logging
import os
from typing import Dict, Any, Optional
from solders.keypair import Keypair
from solders.pubkey import Pubkey
import solders.system_program as system_program
from solders.transaction import Transaction

logger = logging.getLogger(__name__)

class WalletManager:
    """Manages Solana wallets and transactions."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize wallet manager."""
        self.config = config
        self.keypair: Optional[Keypair] = None
        self.initialized = False
        self._connected = False
        
    async def initialize(self, rpc_manager):
        """Initialize wallet manager."""
        try:
            if self.initialized:
                return
                
            logger.info("Initializing wallet manager...")
            
            # Store RPC manager reference
            self.rpc = rpc_manager
            
            # Load or create keypair
            await self._load_keypair()
            
            # Test connection
            await self._test_connection()
            
            self.initialized = True
            logger.info("Wallet manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize wallet manager: {str(e)}")
            await self.cleanup()
            raise
            
    async def _load_keypair(self):
        """Load or create Solana keypair."""
        try:
            # Check for existing keypair file
            keypair_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'keypair.json')
            
            if os.path.exists(keypair_path):
                logger.info("Loading existing keypair...")
                with open(keypair_path, 'r') as f:
                    import json
                    keypair_bytes = bytes(json.load(f))
                    self.keypair = Keypair.from_bytes(keypair_bytes)
            else:
                logger.info("Generating new keypair...")
                self.keypair = Keypair()
                # Save keypair for future use
                os.makedirs(os.path.dirname(keypair_path), exist_ok=True)
                with open(keypair_path, 'w') as f:
                    import json
                    json.dump(list(self.keypair.secret()), f)
                
            logger.info(f"Wallet public key: {self.keypair.pubkey()}")
            
        except Exception as e:
            logger.error(f"Failed to load/create keypair: {str(e)}")
            raise
            
    async def _test_connection(self):
        """Test wallet connection."""
        try:
            if not self.keypair:
                raise Exception("Keypair not initialized")
                
            # Get account info
            response = await self.rpc.client.get_account_info(self.keypair.pubkey())
            if response.value:
                logger.info(f"Account exists with {response.value.lamports / 1e9} SOL")
            else:
                logger.info("Account does not exist yet (needs funding)")
                
            self._connected = True
            
        except Exception as e:
            logger.error(f"Wallet connection test failed: {str(e)}")
            self._connected = False
            raise
            
    async def cleanup(self):
        """Clean up resources."""
        self.initialized = False
        self._connected = False
        
    def is_connected(self) -> bool:
        """Check if wallet is connected."""
        return self._connected
        
    async def get_balance(self) -> float:
        """Get wallet balance in SOL."""
        try:
            if not self.keypair:
                raise Exception("Wallet not initialized")
                
            response = await self.rpc.client.get_balance(self.keypair.pubkey())
            if not response.value:
                return 0.0
            return response.value / 1e9  # Convert lamports to SOL
            
        except Exception as e:
            logger.error(f"Failed to get balance: {str(e)}")
            return 0.0
            
    async def get_token_balance(self, token_mint: str) -> float:
        """Get token balance for a specific SPL token."""
        try:
            if not self.keypair:
                raise Exception("Wallet not initialized")
                
            # Get token account
            response = await self.rpc.client.get_token_accounts_by_owner(
                self.keypair.pubkey(),
                {"mint": token_mint}
            )
            
            if not response.value:
                return 0.0
                
            # Get balance of first token account
            token_account = response.value[0].pubkey
            balance = await self.rpc.client.get_token_account_balance(token_account)
            
            if not balance.value:
                return 0.0
                
            return float(balance.value.amount)
            
        except Exception as e:
            logger.error(f"Failed to get token balance: {str(e)}")
            return 0.0
            
    async def sign_transaction(self, transaction: Transaction) -> Transaction:
        """Sign a transaction with the wallet keypair."""
        try:
            if not self.keypair:
                raise Exception("Wallet not initialized")
                
            transaction.sign([self.keypair])
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to sign transaction: {str(e)}")
            raise
            
    async def send_transaction(self, transaction: Transaction) -> str:
        """Sign and send a transaction."""
        try:
            if not self.keypair:
                raise Exception("Wallet not initialized")
                
            # Sign transaction
            transaction = await self.sign_transaction(transaction)
            
            # Send transaction
            response = await self.rpc.client.send_transaction(
                transaction,
                [self.keypair]
            )
            
            if not response.value:
                raise Exception("Failed to send transaction")
                
            return response.value
            
        except Exception as e:
            logger.error(f"Failed to send transaction: {str(e)}")
            raise
