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
from solana.rpc.commitment import Confirmed
import time

logger = logging.getLogger(__name__)

class PhantomWalletManager:
    """Manages Phantom wallet integration."""
    
    SOLSCAN_API_BASE = "https://api.solscan.io"
    SOLSCAN_ACCOUNT_ENDPOINT = "/v2/account/{address}"
    SOLANA_RPC = "https://api.mainnet-beta.solana.com"  # Default public RPC
    BACKUP_RPCS = [
        "https://solana-mainnet.g.alchemy.com/v2/demo",  # Alchemy demo endpoint
        "https://api.mainnet-beta.solana.com",  # Solana default
        "https://rpc.ankr.com/solana",  # Ankr public endpoint
    ]
    DEFAULT_WALLET = "8jqv2AKPGYwojLRHQZLokkYdtHycs8HAVGDMqZUvTByB"  # Your wallet address
    
    def __init__(self):
        """Initialize wallet manager."""
        logger.debug("=== BEGIN WALLET MANAGER INITIALIZATION ===")
        try:
            self._pubkey = None
            self._is_connected = False
            self.client = Client(self.SOLANA_RPC)
            logger.debug(f"Initialized wallet manager with RPC: {self.SOLANA_RPC}")
            self.cred_manager = WindowsCredManager()
            self._keypair = None
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
            logger.debug(f"Initializing wallet with address: {address}")
            
            # Validate address format
            try:
                self._pubkey = Pubkey.from_string(address)
                logger.debug(f"Public key created: {self._pubkey}")
            except ValueError as e:
                logger.error(f"Invalid wallet address format: {str(e)}")
                return False, f"Invalid wallet address format: {str(e)}"

            # Test RPC connection with fallback
            success, message = self._test_rpc_connection()
            if not success:
                logger.error(f"All RPC connections failed: {message}")
                return False, f"RPC connection failed: {message}"
            logger.debug("RPC connection successful")

            # Test Solscan connection
            success, message = self._test_solscan_connection()
            if not success:
                logger.warning(f"Solscan connection failed: {message}")
                # Continue anyway as we can fallback to RPC
            else:
                logger.debug("Solscan connection successful")

            # Check if account exists and get initial balance
            try:
                balance_response = self._safe_rpc_call(self.client.get_balance, self._pubkey)
                if not balance_response or not hasattr(balance_response, 'value'):
                    logger.error("Failed to get initial balance")
                    return False, "Failed to get initial balance"
                
                balance = float(balance_response.value) / 10**9
                logger.info(f"Initial wallet balance: {balance} SOL")
                
                if balance <= 0:
                    logger.warning("Wallet has zero balance")
                    return False, "Wallet has zero balance. Please fund the wallet before proceeding."
                
            except Exception as e:
                logger.error(f"Failed to check initial balance: {str(e)}")
                return False, f"Failed to check initial balance: {str(e)}"

            self._is_connected = True
            logger.info(f"Wallet initialized successfully. Address: {address}")
            return True, "Wallet initialized successfully"

        except Exception as e:
            logger.error(f"Wallet initialization failed: {str(e)}")
            logger.error(traceback.format_exc())
            return False, f"Wallet initialization failed: {str(e)}"

    @property
    def pubkey(self) -> Pubkey:
        """Get the public key."""
        if self._pubkey is None:
            raise RuntimeError("Wallet not initialized")
        return self._pubkey

    def _test_rpc_connection(self) -> Tuple[bool, str]:
        """Test RPC connection with fallback to backup RPCs."""
        for rpc in [self.SOLANA_RPC] + self.BACKUP_RPCS:
            try:
                logger.debug(f"Testing RPC connection to {rpc}")
                test_client = Client(rpc)
                
                # Test connection by getting slot
                response = test_client.get_slot()
                if response is not None:
                    logger.info(f"Successfully connected to RPC {rpc}")
                    self.client = test_client  # Update client to working RPC
                    self.SOLANA_RPC = rpc     # Update RPC URL
                    return True, f"Connected to {rpc}"
            except Exception as e:
                logger.warning(f"Failed to connect to RPC {rpc}: {str(e)}")
                continue
        
        return False, "All RPC endpoints failed"

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
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request headers: {headers}")
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.error(f"Solscan API error: {response.status_code} - {response.text}")
                return None
                
            data = response.json()
            logger.debug(f"Solscan account info: {json.dumps(data, indent=2)}")
            
            if 'status' in data and data['status'] != 200:
                logger.error(f"Solscan API returned error status: {data}")
                return None
                
            return data
            
        except requests.exceptions.Timeout:
            logger.error("Solscan API request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error with Solscan API: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Solscan response: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to get Solscan account info: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def _safe_rpc_call(self, fn, *args):
        """Safely make an RPC call with retries."""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                result = fn(*args)
                return result
            except InvalidParamsMessage as e:
                logger.error(f"RPC Invalid Params: {str(e)}")
                return None
            except Exception as e:
                logger.error(f"RPC Error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                return None

    def get_balance(self) -> float:
        """Get wallet SOL balance."""
        if not self._is_connected:
            logger.error("Wallet not connected")
            raise RuntimeError("Wallet not connected")
            
        try:
            address = str(self._pubkey)
            logger.debug(f"Checking balance for {address}")
            
            # Try RPC first as it's more reliable
            balance_response = self._safe_rpc_call(self.client.get_balance, self._pubkey)
            if balance_response and hasattr(balance_response, 'value'):
                balance = float(balance_response.value) / 10**9
                logger.info(f"Got balance from RPC: {balance} SOL")
                return balance
            
            # Fallback to Solscan if RPC fails
            logger.debug("RPC balance check failed, trying Solscan")
            account_info = self._get_solscan_account_info(address)
            if account_info and 'lamports' in account_info:
                balance = float(account_info['lamports']) / 10**9
                logger.info(f"Got balance from Solscan: {balance} SOL")
                return balance
            
            logger.error("Failed to get balance from both RPC and Solscan")
            return 0.0

        except Exception as e:
            logger.error(f"Error getting wallet balance: {str(e)}")
            logger.error(traceback.format_exc())
            return 0.0

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
