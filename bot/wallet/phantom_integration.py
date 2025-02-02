"""Phantom wallet integration for Solana trading."""

from solders.keypair import Keypair
from solana.rpc.api import Client
from solders.rpc.responses import GetBalanceResp
from solders.pubkey import Pubkey
from bot.security.win_credentials import WindowsCredManager
import logging
import binascii
import traceback
import requests
import json
import os
from typing import Optional, Dict, Any, Tuple
import base58
from solana.rpc.types import TxOpts
from solders.rpc.errors import InvalidParamsMessage

logger = logging.getLogger(__name__)

class PhantomWalletManager:
    """Manages Phantom wallet integration."""
    
    SOLSCAN_API_BASE = "https://api.solscan.io"
    SOLSCAN_ACCOUNT_ENDPOINT = "/v2/account/{address}"
    SOLANA_RPC = "https://api.mainnet-beta.solana.com"
    DEFAULT_WALLET = "8jqv2AKPGYwojLRHQZLokkYdtHycs8HAVGDMqZUvTByB"  # Your wallet address
    
    def __init__(self):
        """Initialize wallet manager."""
        logger.debug("=== BEGIN WALLET MANAGER INITIALIZATION ===")
        try:
            self.client = Client(self.SOLANA_RPC)
            self.cred_manager = WindowsCredManager()
            self._keypair = None
            self._pubkey = None
            self._is_connected = False
            self._solscan_api_key = os.getenv('SOLSCAN_API_KEY')
            logger.debug("PhantomWalletManager basic initialization complete")
            
            # Try to initialize with default wallet
            self.initialize_with_address(self.DEFAULT_WALLET)
        except Exception as e:
            logger.error(f"Failed to initialize PhantomWalletManager: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Wallet initialization failed: {str(e)}")
        logger.debug("=== END WALLET MANAGER INITIALIZATION ===")

    def initialize_with_address(self, address: str) -> Tuple[bool, str]:
        """Initialize wallet with a public address."""
        try:
            from solders.pubkey import Pubkey
            import base58
            
            # Convert address string to Pubkey
            try:
                decoded = base58.b58decode(address)
                self._pubkey = Pubkey(decoded)
                logger.info(f"Converted address to Pubkey: {self._pubkey}")
            except Exception as e:
                logger.error(f"Failed to convert address to Pubkey: {str(e)}")
                return False, f"Invalid wallet address format: {str(e)}"

            # Test connection by checking balance
            try:
                balance = self.client.get_balance(self._pubkey)
                logger.info(f"Initial balance check successful: {balance.value if balance else 0} lamports")
                self._is_connected = True
                return True, "Wallet initialized successfully"
            except Exception as e:
                logger.error(f"Balance check failed: {str(e)}")
                return False, f"Balance check failed: {str(e)}"
                
        except Exception as e:
            logger.error(f"Wallet initialization failed: {str(e)}")
            return False, f"Wallet initialization failed: {str(e)}"

    @property
    def pubkey(self) -> Pubkey:
        """Get the public key."""
        if self._pubkey is None:
            raise RuntimeError("Wallet not initialized")
        return self._pubkey

    def _test_rpc_connection(self) -> Tuple[bool, str]:
        """Test RPC connection."""
        try:
            # Test basic connection
            response = self.client.get_version()
            logger.debug(f"RPC Version response: {response}")
            return True, "RPC connection successful"
        except Exception as e:
            error_msg = f"RPC connection failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return False, error_msg

    def _test_solscan_connection(self) -> Tuple[bool, str]:
        """Test Solscan API connection."""
        try:
            headers = {'Accept': 'application/json'}
            if self._solscan_api_key:
                headers['token'] = self._solscan_api_key

            # Test with default wallet address
            url = f"{self.SOLSCAN_API_BASE}{self.SOLSCAN_ACCOUNT_ENDPOINT.format(address=self.DEFAULT_WALLET)}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            logger.debug("Solscan connection successful")
            return True, "Solscan connection successful"
        except Exception as e:
            error_msg = f"Solscan connection failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return False, error_msg

    def _get_solscan_account_info(self, address: str) -> Optional[Dict[str, Any]]:
        """Get account information from Solscan."""
        try:
            headers = {'Accept': 'application/json'}
            if self._solscan_api_key:
                headers['token'] = self._solscan_api_key

            url = f"{self.SOLSCAN_API_BASE}{self.SOLSCAN_ACCOUNT_ENDPOINT.format(address=address)}"
            logger.debug(f"Requesting Solscan info for address: {address}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Solscan account info: {json.dumps(data, indent=2)}")
            return data
        except Exception as e:
            logger.error(f"Failed to get Solscan account info: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def _safe_rpc_call(self, fn, *args):
        try:
            return fn(*args)
        except InvalidParamsMessage as e:
            logger.error(f"RPC Invalid Params: {str(e)}")
        except Exception as e:
            logger.error(f"RPC Error: {str(e)}")
        return None

    def get_balance(self) -> float:
        """Get wallet SOL balance."""
        if not self._is_connected:
            raise RuntimeError("Wallet not connected")
            
        try:
            address = str(self._pubkey)
            logger.debug(f"Checking balance for {address}")
            
            # Try Solscan first for more detailed info
            account_info = self._get_solscan_account_info(address)
            if account_info and 'lamports' in account_info:
                return float(account_info['lamports']) / 10**9
            
            # Fallback to RPC
            balance_resp = self._safe_rpc_call(self.client.get_balance, address)
            if balance_resp is None:
                raise RuntimeError("Failed to get balance")
            if not isinstance(balance_resp, GetBalanceResp):
                raise RuntimeError("Invalid response type from get_balance")
                
            return balance_resp.value / 10**9  # Convert lamports to SOL
        except Exception as e:
            logger.error(f"Balance check failed: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def get_token_balances(self) -> Dict[str, float]:
        """Get all token balances for the wallet."""
        if not self._is_connected:
            raise RuntimeError("Wallet not connected")
            
        try:
            address = str(self._pubkey)
            account_info = self._get_solscan_account_info(address)
            
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

    def connect(self) -> Tuple[bool, str]:
        """Connect to Solana network."""
        try:
            logger.debug("Attempting to connect to Solana network")
            
            # If already connected, return success
            if self._is_connected and self._pubkey is not None:
                return True, "Already connected"
            
            # Initialize with default wallet address
            return self.initialize_with_address(self.DEFAULT_WALLET)
                
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self._is_connected = False
            return False, error_msg
            
    def is_connected(self) -> bool:
        """Check if wallet is connected."""
        return self._is_connected and self._pubkey is not None
        
    def get_explorer_url(self, pubkey: Optional[str] = None) -> str:
        """Get Solscan explorer URL for the wallet or a specific address."""
        if pubkey is None and self._pubkey is not None:
            pubkey = str(self._pubkey)
        if pubkey:
            return f"https://solscan.io/account/{pubkey}"
        return "https://solscan.io"
