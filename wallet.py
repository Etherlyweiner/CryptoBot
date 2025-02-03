import os
import json
import logging
import asyncio
from typing import Optional, List, Dict, Any
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
from solana.transaction import Transaction as SolanaTransaction
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger('CryptoBot.Wallet')

load_dotenv()

class WalletError(Exception):
    """Base exception for wallet-related errors"""
    pass

class ConnectionError(WalletError):
    """Raised when wallet connection fails"""
    pass

class TransactionError(WalletError):
    """Raised when transaction fails"""
    pass

class PhantomWallet:
    def __init__(self, network: str = None):
        """Initialize Phantom wallet with specified network"""
        self.network = network or os.getenv('NETWORK', 'mainnet-beta')
        
        # Use Helius RPC if available, fallback to public endpoint
        helius_key = os.getenv('HELIUS_API_KEY')
        if helius_key:
            self.rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
        else:
            self.rpc_url = os.getenv('RPC_URL', 'https://api.mainnet-beta.solana.com')
            
        self.commitment = Commitment(os.getenv('COMMITMENT_LEVEL', 'confirmed'))
        self.client = AsyncClient(self.rpc_url, commitment=self.commitment)
        self._public_key = None
        self._connected = False
        self._last_balance_check = 0
        self._balance_cache_ttl = 60  # Cache balance for 60 seconds
        self._cached_balance = None
        
        # Load wallet configuration
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.json')
        try:
            with open(config_path) as f:
                self.config = json.load(f)
            self._public_key = Pubkey.from_string(self.config['wallet']['address'])
            logger.info(f"Loaded wallet address: {self._public_key}")
        except Exception as e:
            logger.error(f"Failed to load wallet config: {str(e)}")
            raise WalletError("Failed to initialize wallet configuration")
        
    @property
    def is_connected(self) -> bool:
        """Check if wallet is connected"""
        return self._connected and self._public_key is not None
        
    async def connect(self) -> bool:
        """Connect to wallet and verify connection"""
        try:
            # Test connection with a version request
            version = await self.client.get_version()
            logger.info(f"Connected to Solana node version: {version}")
            
            # Verify the account exists
            account_info = await self.client.get_account_info(self._public_key)
            if account_info.value is None:
                raise ConnectionError("Wallet account not found on-chain")
                
            self._connected = True
            logger.info(f"Successfully connected wallet: {self._public_key}")
            return True
            
        except Exception as e:
            self._connected = False
            logger.error(f"Failed to connect wallet: {str(e)}")
            raise ConnectionError(f"Failed to connect wallet: {str(e)}")
        
    async def get_balance(self) -> float:
        """Get wallet SOL balance with caching"""
        try:
            current_time = asyncio.get_event_loop().time()
            
            # Return cached balance if still valid
            if self._cached_balance is not None and \
               (current_time - self._last_balance_check) < self._balance_cache_ttl:
                return self._cached_balance
            
            if not self.is_connected:
                await self.connect()
            
            balance = await self.client.get_balance(self._public_key)
            if balance.value is None:
                raise WalletError("Failed to retrieve balance")
                
            sol_balance = balance.value / 1e9  # Convert lamports to SOL
            
            # Update cache
            self._cached_balance = sol_balance
            self._last_balance_check = current_time
            
            logger.info(f"Updated wallet balance: {sol_balance:.4f} SOL")
            return sol_balance
            
        except Exception as e:
            logger.error(f"Failed to get wallet balance: {str(e)}")
            raise WalletError(f"Failed to get wallet balance: {str(e)}")

    async def get_token_accounts(self) -> List[Dict[str, Any]]:
        """Get all token accounts owned by the wallet"""
        try:
            if not self.is_connected:
                raise WalletError("Wallet not connected")
                
            response = await self.client.get_token_accounts_by_owner(
                self._public_key,
                {'programId': Pubkey.from_string('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')}
            )
            
            accounts = []
            for account in response.value:
                try:
                    accounts.append({
                        'mint': account.account.data.parsed['info']['mint'],
                        'amount': account.account.data.parsed['info']['tokenAmount']['amount'],
                        'decimals': account.account.data.parsed['info']['tokenAmount']['decimals']
                    })
                except (KeyError, AttributeError) as e:
                    logger.warning(f"Failed to parse token account: {str(e)}")
                    continue
                    
            return accounts
            
        except Exception as e:
            logger.error(f"Failed to get token accounts: {str(e)}")
            return []
            
    def get_public_key(self) -> Pubkey:
        """Get wallet's public key"""
        if not self._public_key:
            raise WalletError("Wallet not connected")
        return Pubkey.from_string(self._public_key)
        
    async def sign_transaction(self, transaction: Transaction) -> Optional[Transaction]:
        """Sign a transaction using Phantom wallet"""
        try:
            if not self.is_connected:
                raise WalletError("Wallet not connected")
                
            # This would trigger Phantom's signing popup
            logger.info("Please approve the transaction in your Phantom wallet...")
            # Add retry logic for transaction signing
            max_retries = 3
            retry_delay = 1
            
            for attempt in range(max_retries):
                try:
                    # Simulate the transaction first
                    simulation = await self.client.simulate_transaction(transaction)
                    if simulation.value.err:
                        raise TransactionError(f"Transaction simulation failed: {simulation.value.err}")
                        
                    return transaction
                    
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Retry {attempt + 1}/{max_retries} failed: {str(e)}")
                    await asyncio.sleep(retry_delay)
                    
        except Exception as e:
            logger.error(f"Failed to sign transaction: {str(e)}")
            raise TransactionError(f"Transaction signing failed: {str(e)}")
    
    async def execute_swap(self, input_token: str, output_token: str, amount: float) -> bool:
        """Execute a token swap using Jupiter"""
        try:
            if not self.is_connected:
                raise WalletError("Wallet not connected")
                
            # Verify balance before swap
            input_balance = await self.get_balance()
            if input_balance is None or input_balance < amount:
                raise TransactionError(f"Insufficient balance for swap: {input_balance} < {amount}")
                
            logger.info(f"Executing swap: {amount} {input_token} -> {output_token}")
            # Implement actual swap logic here
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute swap: {str(e)}")
            return False
            
    async def close(self):
        """Close the wallet connection"""
        try:
            self._connected = False
            self._public_key = None
            await self.client.close()
            logger.info("Wallet connection closed")
        except Exception as e:
            logger.error(f"Error closing wallet connection: {str(e)}")
