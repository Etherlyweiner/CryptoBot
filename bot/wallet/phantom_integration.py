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
        self.session: Optional[aiohttp.ClientSession] = None
        wallet_address = config.get('wallet', {}).get('address')
        if not wallet_address:
            raise ValueError("Wallet address not found in config")
            
        # Convert string address to Pubkey
        try:
            self.wallet_address = Pubkey.from_string(wallet_address)
            logger.info(f"Initialized wallet with address: {str(self.wallet_address)}")
        except ValueError as e:
            raise ValueError(f"Invalid wallet address: {str(e)}")
            
        # Get Helius API configuration
        helius_config = config.get('api_keys', {}).get('helius', {})
        if not helius_config or not helius_config.get('key'):
            raise ValueError("Helius API key not found in config")
            
        # Initialize RPC endpoints with priority
        self.rpc_endpoints: List[str] = []
        
        # Add Helius endpoints first (they're more reliable)
        if helius_config.get('staked_rpc'):
            logger.info("Added Helius primary RPC endpoint")
            self.rpc_endpoints.append(helius_config['staked_rpc'])
            
        if helius_config.get('standard_rpc'):
            logger.info("Added Helius standard RPC endpoint")
            self.rpc_endpoints.append(helius_config['standard_rpc'])
            
        # Add fallback RPC endpoints
        network_endpoints = config.get('network', {}).get('rpc_endpoints', [])
        if network_endpoints:
            logger.info(f"Added {len(network_endpoints)} fallback RPC endpoints")
            self.rpc_endpoints.extend(network_endpoints)
            
        if not self.rpc_endpoints:
            # Add default Solana RPC as last resort
            logger.info("Added default Solana RPC fallback")
            self.rpc_endpoints.append("https://api.mainnet-beta.solana.com")
            
        self.current_endpoint_index = 0
        self.last_balance_check = datetime.min
        self.balance_cache_duration = 60  # Cache balance for 60 seconds
        
    async def __aenter__(self):
        """Async context manager entry."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None
            
    def _get_next_endpoint(self) -> str:
        """Get next RPC endpoint with round-robin."""
        endpoint = self.rpc_endpoints[self.current_endpoint_index]
        self.current_endpoint_index = (self.current_endpoint_index + 1) % len(self.rpc_endpoints)
        return endpoint
        
    async def _make_rpc_request(
        self,
        method: str,
        params: list,
        retries: int = 3
    ) -> Tuple[bool, Any]:
        """Make RPC request with failover and retries.
        
        Args:
            method: RPC method name
            params: List of parameters
            retries: Number of retries per endpoint
            
        Returns:
            Tuple of (success, result/error_message)
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        # Try each endpoint
        for endpoint in self.rpc_endpoints:
            logger.debug(f"Trying RPC endpoint: {endpoint}")
            
            for attempt in range(retries):
                try:
                    payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": method,
                        "params": params
                    }
                    
                    async with self.session.post(
                        endpoint,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 429:  # Rate limit
                            retry_after = int(response.headers.get('Retry-After', 5))
                            logger.warning(f"Rate limited by {endpoint}, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            continue
                            
                        if response.status == 522:  # Cloudflare timeout
                            logger.warning(f"Cloudflare timeout from {endpoint}")
                            await asyncio.sleep(2 ** attempt)
                            continue
                            
                        if response.status != 200:
                            error_text = await response.text()
                            logger.warning(f"Error from {endpoint}: {response.status} - {error_text}")
                            break  # Try next endpoint
                            
                        data = await response.json()
                        
                        if "error" in data:
                            error = data["error"]
                            logger.warning(f"RPC error from {endpoint}: {error}")
                            break  # Try next endpoint
                            
                        return True, data.get("result")
                        
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout from {endpoint} (attempt {attempt + 1}/{retries})")
                    if attempt < retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        
                except Exception as e:
                    logger.error(f"Error from {endpoint}: {str(e)}")
                    if attempt < retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        
        return False, "All RPC endpoints failed"
        
    async def connect(self) -> Tuple[bool, str]:
        """Connect to the wallet.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            async with self as wallet:
                # Test connection by getting SOL balance
                success, balance = await wallet.get_sol_balance()
                if not success:
                    return False, f"Failed to connect to wallet: {balance}"
                    
                logger.info(f"Successfully connected to wallet {self.wallet_address}")
                logger.info(f"Current SOL balance: {balance:.9f}")
                return True, "Connected successfully"
                
        except Exception as e:
            logger.error(f"Error connecting to wallet: {str(e)}")
            return False, str(e)
            
    async def get_sol_balance(self) -> Tuple[bool, float]:
        """Get SOL balance for the wallet.
        
        Returns:
            Tuple of (success, balance/error_message)
        """
        try:
            # Check cache
            now = datetime.now()
            if hasattr(self, '_cached_balance') and \
               (now - self.last_balance_check).total_seconds() < self.balance_cache_duration:
                return True, self._cached_balance
                
            success, result = await self._make_rpc_request(
                "getBalance",
                [str(self.wallet_address)]
            )
            
            if not success:
                return False, result
                
            # Handle different response formats
            if isinstance(result, dict):
                balance_value = result.get('value', 0)
            else:
                balance_value = result or 0
                
            # Convert lamports to SOL
            balance = float(balance_value) / 1e9
            
            # Update cache
            self._cached_balance = balance
            self.last_balance_check = now
            
            return True, balance
            
        except Exception as e:
            logger.error(f"Error getting SOL balance: {str(e)}")
            return False, str(e)
            
    async def get_token_balance(self, token_address: str) -> Tuple[bool, float]:
        """Get token balance for the wallet.
        
        Args:
            token_address: Token mint address
            
        Returns:
            Tuple of (success, balance/error_message)
        """
        try:
            success, result = await self._make_rpc_request(
                "getTokenAccountsByOwner",
                [
                    str(self.wallet_address),
                    {"mint": token_address},
                    {"encoding": "jsonParsed"}
                ]
            )
            
            if not success:
                return False, result
                
            if not result or not result.get('value'):
                return True, 0.0
                
            # Get token account with highest balance
            max_balance = 0
            for account in result['value']:
                info = account.get('account', {}).get('data', {}).get('parsed', {}).get('info', {})
                balance = float(info.get('tokenAmount', {}).get('amount', 0))
                decimals = int(info.get('tokenAmount', {}).get('decimals', 0))
                max_balance = max(max_balance, balance / (10 ** decimals))
                
            return True, max_balance
            
        except Exception as e:
            logger.error(f"Error getting token balance: {str(e)}")
            return False, str(e)
            
    async def sign_transaction(self, transaction: Dict[str, Any]) -> Tuple[bool, str]:
        """Sign a transaction.
        
        Args:
            transaction: Transaction data
            
        Returns:
            Tuple of (success, signature/error_message)
        """
        # TODO: Implement transaction signing
        raise NotImplementedError("Transaction signing not yet implemented")
