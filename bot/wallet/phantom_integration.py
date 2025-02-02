"""Phantom wallet integration for Solana trading."""

from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from bot.security.win_credentials import WindowsCredManager
import logging
import asyncio
import binascii

logger = logging.getLogger(__name__)

class PhantomWalletManager:
    def __init__(self):
        """Initialize wallet manager."""
        self.client = AsyncClient("https://api.mainnet-beta.solana.com")
        self.cred_manager = WindowsCredManager()
        self.keypair = None  # Deferred initialization
        logger.debug("PhantomWalletManager initialized")

    def _debug_keypair(self, keypair: bytes, name: str) -> None:
        """Debug helper for keypair data."""
        try:
            logger.debug(f"{name} length: {len(keypair)}")
            logger.debug(f"{name} hex: {binascii.hexlify(keypair).decode()}")
            logger.debug(f"{name} first 8 bytes: {list(keypair[:8])}")
        except Exception as e:
            logger.error(f"Failed to debug {name}: {str(e)}")

    async def ensure_initialized(self):
        """Ensure wallet is initialized."""
        if not self.keypair:
            try:
                logger.debug("Loading keypair from secure storage")
                secret_bytes = self.cred_manager.get_credentials('PhantomBotKey')
                self._debug_keypair(secret_bytes, "Retrieved secret")
                
                # Create keypair from secret bytes
                keypair = Keypair.from_bytes(secret_bytes)
                self.keypair = keypair
                logger.debug(f"Loaded keypair with public key: {self.keypair.pubkey()}")
            except Exception as e:
                logger.error(f"Failed to load keypair: {str(e)}", exc_info=True)
                raise RuntimeError("Wallet not initialized - call initialize_wallet() first")

    async def initialize_wallet(self, secret_bytes: bytes):
        """Initialize wallet with secret bytes."""
        try:
            logger.debug("=== BEGIN WALLET INITIALIZATION ===")
            self._debug_keypair(secret_bytes, "Input secret")
            
            # Store the secret bytes
            logger.debug("Storing keypair in credential manager")
            self.cred_manager.store_phantom_credentials(secret_bytes)
            
            # Create keypair from secret
            logger.debug("Creating Solana keypair")
            keypair = Keypair.from_bytes(secret_bytes)
            self.keypair = keypair
            logger.debug(f"Created keypair with public key: {self.keypair.pubkey()}")
            
            # Test connection
            logger.debug("Testing connection with balance check")
            balance = await self.client.get_balance(self.keypair.pubkey())
            logger.debug(f"Connection test successful. Balance: {balance.value / 10**9} SOL")
            logger.debug("=== END WALLET INITIALIZATION ===")
            
        except Exception as e:
            logger.error(f"Wallet initialization failed: {str(e)}", exc_info=True)
            raise

    async def get_balance(self) -> float:
        """Get wallet SOL balance."""
        await self.ensure_initialized()
        try:
            balance = await self.client.get_balance(self.keypair.pubkey())
            return balance.value / 10**9  # Convert lamports to SOL
        except Exception as e:
            logger.error(f"Balance check failed: {str(e)}", exc_info=True)
            raise

    async def connect(self):
        """Connect to Solana network."""
        if self.client.is_closed():
            self.client = AsyncClient("https://api.mainnet-beta.solana.com")
