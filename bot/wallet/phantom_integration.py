"""Phantom wallet integration for Solana trading."""

from solders.keypair import Keypair
from solana.rpc.api import Client
from solders.rpc.responses import GetBalanceResp
from solders.pubkey import Pubkey
from bot.security.win_credentials import WindowsCredManager
import logging
import traceback
from typing import Dict, Any, Optional, Tuple
import requests
from ..api.solscan_client import SolscanClient
import binascii
import json
import os
from solana.rpc.types import TxOpts
from solders.rpc.errors import InvalidParamsMessage
from solana.rpc.commitment import Confirmed
import time
import base58

logger = logging.getLogger(__name__)

class PhantomWalletManager:
    """Manages Phantom wallet integration."""
    
    SOLANA_RPC = "https://api.mainnet-beta.solana.com"  # Default public RPC
    BACKUP_RPCS = [
        "https://solana-mainnet.g.alchemy.com/v2/demo",  # Alchemy demo endpoint
        "https://api.mainnet-beta.solana.com",  # Solana default
        "https://rpc.ankr.com/solana",  # Ankr public endpoint
    ]
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """Initialize wallet manager."""
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self._solscan_api_key = config.get('api_keys', {}).get('solscan', {}).get('key')
        self.SOLSCAN_API_BASE = config.get('api_keys', {}).get('solscan', {}).get('base_url', 'https://api.solscan.io')
        self.DEFAULT_WALLET = config.get('wallet', {}).get('address', '8jqv2AKPGYwojLRHQZLokkYdtHycs8HAVGDMqZUvTByB')
        
        # Initialize Solscan client
        self.solscan = SolscanClient(
            api_key=self._solscan_api_key,
            base_url=self.SOLSCAN_API_BASE
        )
        
        self.logger.debug("=== BEGIN WALLET MANAGER INITIALIZATION ===")
        try:
            self._pubkey = None
            self._is_connected = False
            self._rpc_client = Client(self.SOLANA_RPC)
            self.logger.debug(f"Initialized wallet manager with RPC: {self.SOLANA_RPC}")
            self.cred_manager = WindowsCredManager()
            self._keypair = None
            self.logger.debug("PhantomWalletManager basic initialization complete")
            
            # Try to initialize with default wallet
            self._initialize_default_wallet()
            
        except Exception as e:
            self.logger.error(f"Error initializing wallet manager: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise
            
    def _initialize_default_wallet(self):
        """Initialize wallet with default address."""
        try:
            logger.debug(f"Initializing wallet with address: {self.DEFAULT_WALLET}")
            
            # Validate address format
            try:
                self._pubkey = Pubkey.from_string(self.DEFAULT_WALLET)
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
                balance_response = self._safe_rpc_call(self._rpc_client.get_balance, self._pubkey)
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
            logger.info(f"Wallet initialized successfully. Address: {self.DEFAULT_WALLET}")
            return True, "Wallet initialized successfully"

        except Exception as e:
            logger.error(f"Wallet initialization failed: {str(e)}")
            logger.error(traceback.format_exc())
            return False, f"Wallet initialization failed: {str(e)}"

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
                balance_response = self._safe_rpc_call(self._rpc_client.get_balance, self._pubkey)
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
                    self._rpc_client = test_client  # Update client to working RPC
                    self.SOLANA_RPC = rpc     # Update RPC URL
                    return True, f"Connected to {rpc}"
            except Exception as e:
                logger.warning(f"Failed to connect to RPC {rpc}: {str(e)}")
                continue
        
        return False, "All RPC endpoints failed"

    def _test_solscan_connection(self) -> Tuple[bool, str]:
        """Test connection to Solscan API."""
        try:
            if self.solscan.test_connection():
                self.logger.debug("Solscan connection successful")
                return True, "Solscan connection successful"
            return False, "Solscan connection test failed"
        except Exception as e:
            error_msg = f"Solscan connection failed: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            return False, error_msg
            
    def _get_solscan_account_info(self, address: str) -> Optional[Dict[str, Any]]:
        """Get account information from Solscan."""
        try:
            return self.solscan.get_account_info(address)
        except Exception as e:
            self.logger.error(f"Failed to get Solscan account info: {str(e)}")
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
            balance_response = self._safe_rpc_call(self._rpc_client.get_balance, self._pubkey)
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
            return self._initialize_default_wallet()
                
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
