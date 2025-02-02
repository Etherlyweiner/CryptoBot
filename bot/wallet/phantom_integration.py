"""Phantom wallet integration for Solana trading."""

from solders.keypair import Keypair
from solana.rpc.api import Client
from solders.rpc.responses import GetBalanceResp
from bot.security.win_credentials import WindowsCredManager
import logging
import binascii
import traceback
import requests
import json
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class PhantomWalletManager:
    """Manages Phantom wallet integration."""
    
    SOLSCAN_API_BASE = "https://public-api.solscan.io"
    SOLANA_RPC = "https://api.mainnet-beta.solana.com"
    
    def __init__(self):
        """Initialize wallet manager."""
        logger.debug("=== BEGIN WALLET MANAGER INITIALIZATION ===")
        self.client = Client(self.SOLANA_RPC)
        self.cred_manager = WindowsCredManager()
        self._keypair = None
        self._is_connected = False
        self._solscan_api_key = os.getenv('SOLSCAN_API_KEY')  # Optional API key for higher rate limits
        logger.debug("PhantomWalletManager basic initialization complete")
        logger.debug("=== END WALLET MANAGER INITIALIZATION ===")

    @property
    def keypair(self) -> Keypair:
        """Get the keypair, ensuring initialization."""
        if self._keypair is None:
            logger.error("Keypair accessed before initialization!")
            raise RuntimeError("Wallet not initialized - call initialize_wallet() first")
        return self._keypair

    def _debug_keypair(self, keypair: bytes, name: str) -> None:
        """Debug helper for keypair data."""
        try:
            logger.debug(f"{name} length: {len(keypair)}")
            logger.debug(f"{name} hex: {binascii.hexlify(keypair).decode()}")
            logger.debug(f"{name} first 8 bytes: {list(keypair[:8])}")
        except Exception as e:
            logger.error(f"Failed to debug {name}: {str(e)}")
            logger.error(traceback.format_exc())

    def _get_solscan_account_info(self, address: str) -> Optional[Dict[str, Any]]:
        """Get account information from Solscan."""
        try:
            headers = {'Accept': 'application/json'}
            if self._solscan_api_key:
                headers['token'] = self._solscan_api_key

            url = f"{self.SOLSCAN_API_BASE}/account/{address}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Solscan account info: {json.dumps(data, indent=2)}")
            return data
        except Exception as e:
            logger.error(f"Failed to get Solscan account info: {str(e)}")
            return None

    def initialize_wallet(self, secret_bytes: bytes) -> bool:
        """Initialize wallet with secret bytes."""
        try:
            logger.debug("=== BEGIN WALLET INITIALIZATION ===")
            self._debug_keypair(secret_bytes, "Input secret")
            
            # Store the secret bytes
            logger.debug("Storing keypair in credential manager")
            self.cred_manager.store_phantom_credentials(secret_bytes)
            
            # Create keypair from secret
            logger.debug("Creating Solana keypair")
            seed = secret_bytes[:32]  # Use first 32 bytes as seed
            self._keypair = Keypair.from_seed(seed)
            
            # Verify keypair was created
            if self._keypair is None:
                raise RuntimeError("Failed to create keypair")
                
            pubkey = self._keypair.pubkey()
            logger.debug(f"Created keypair with public key: {pubkey}")
            
            # Get account info from Solscan
            account_info = self._get_solscan_account_info(str(pubkey))
            if account_info:
                logger.debug("Successfully retrieved account info from Solscan")
                
            # Test connection with RPC
            logger.debug("Testing RPC connection with balance check")
            try:
                balance_resp = self.client.get_balance(str(pubkey))
                if not isinstance(balance_resp, GetBalanceResp):
                    raise RuntimeError("Invalid response type from get_balance")
                
                balance = balance_resp.value / 10**9  # Convert lamports to SOL
                logger.debug(f"Connection test successful. Balance: {balance} SOL")
                self._is_connected = True
            except Exception as e:
                logger.error(f"Balance check failed: {str(e)}")
                logger.error(traceback.format_exc())
                # Don't raise here - wallet might be valid but empty
            
            logger.debug("=== END WALLET INITIALIZATION ===")
            return True
            
        except Exception as e:
            logger.error("=== WALLET INITIALIZATION FAILED ===")
            logger.error(f"Error: {str(e)}")
            logger.error(traceback.format_exc())
            self._keypair = None
            self._is_connected = False
            raise

    def get_balance(self) -> float:
        """Get wallet SOL balance."""
        if self._keypair is None:
            raise RuntimeError("Wallet not initialized - call initialize_wallet() first")
            
        try:
            pubkey = self._keypair.pubkey()
            logger.debug(f"Checking balance for {pubkey}")
            
            # Try Solscan first for more detailed info
            account_info = self._get_solscan_account_info(str(pubkey))
            if account_info and 'lamports' in account_info:
                return float(account_info['lamports']) / 10**9
            
            # Fallback to RPC
            balance_resp = self.client.get_balance(str(pubkey))
            if not isinstance(balance_resp, GetBalanceResp):
                raise RuntimeError("Invalid response type from get_balance")
                
            return balance_resp.value / 10**9  # Convert lamports to SOL
        except Exception as e:
            logger.error(f"Balance check failed: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def get_token_balances(self) -> Dict[str, float]:
        """Get all token balances for the wallet."""
        if self._keypair is None:
            raise RuntimeError("Wallet not initialized - call initialize_wallet() first")
            
        try:
            pubkey = str(self._keypair.pubkey())
            account_info = self._get_solscan_account_info(pubkey)
            
            if not account_info:
                return {}
                
            token_balances = {}
            if 'tokenInfo' in account_info:
                for token in account_info['tokenInfo']:
                    symbol = token.get('symbol', 'Unknown')
                    balance = float(token.get('balance', 0))
                    decimals = int(token.get('decimals', 9))
                    token_balances[symbol] = balance / (10 ** decimals)
                    
            return token_balances
        except Exception as e:
            logger.error(f"Failed to get token balances: {str(e)}")
            return {}

    def connect(self) -> bool:
        """Connect to Solana network."""
        try:
            logger.debug("Attempting to connect to Solana network")
            
            # If we don't have a keypair, try to load from credentials
            if self._keypair is None:
                try:
                    secret_bytes = self.cred_manager.get_credentials('PhantomBotKey')
                    if secret_bytes:
                        logger.debug("Found existing credentials, initializing wallet")
                        return self.initialize_wallet(secret_bytes)
                except Exception as e:
                    logger.error(f"Failed to load existing credentials: {str(e)}")
                    return False
            
            # Test connection with Solscan and RPC
            if self._keypair:
                pubkey = str(self._keypair.pubkey())
                logger.debug(f"Testing connection for {pubkey}")
                
                # Check Solscan connection
                account_info = self._get_solscan_account_info(pubkey)
                if account_info:
                    logger.debug("Successfully connected to Solscan")
                
                # Check RPC connection
                balance_resp = self.client.get_balance(pubkey)
                if isinstance(balance_resp, GetBalanceResp):
                    balance = balance_resp.value / 10**9
                    logger.debug(f"Successfully connected to RPC. Balance: {balance} SOL")
                    self._is_connected = True
                    return True
                    
            logger.error("No wallet initialized and no saved credentials found")
            return False
                
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            logger.error(traceback.format_exc())
            self._is_connected = False
            return False
            
    def is_connected(self) -> bool:
        """Check if wallet is connected."""
        return self._is_connected and self._keypair is not None
        
    def get_explorer_url(self, pubkey: Optional[str] = None) -> str:
        """Get Solscan explorer URL for the wallet or a specific address."""
        if pubkey is None and self._keypair:
            pubkey = str(self._keypair.pubkey())
        if pubkey:
            return f"https://solscan.io/account/{pubkey}"
        return "https://solscan.io"
