"""Solana Token Program client implementation."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from anchorpy import Program, Provider, Wallet
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey
from solders.system_program import ID as SYS_PROGRAM_ID
from solders.sysvar import RENT

logger = logging.getLogger(__name__)

class TokenProgramClient:
    """Client for interacting with Solana Token Program."""
    
    def __init__(self, 
                 rpc_url: str,
                 wallet: Wallet,
                 idl_path: Optional[str] = None,
                 commitment: str = Confirmed):
        """Initialize Token Program client.
        
        Args:
            rpc_url: Solana RPC URL
            wallet: Solana wallet
            idl_path: Path to IDL file
            commitment: Transaction commitment level
        """
        self.rpc_url = rpc_url
        self.wallet = wallet
        self.commitment = commitment
        
        # Load IDL
        if idl_path is None:
            idl_path = Path(__file__).parent.parent.parent / "idl" / "token_program.json"
        
        with open(idl_path) as f:
            self.idl = json.load(f)
            
        # Initialize program
        self.connection = AsyncClient(rpc_url, commitment=commitment)
        self.provider = Provider(self.connection, wallet)
        self.program = Program(self.idl, Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"), self.provider)
        
    async def get_token_account(self, token_address: str, owner_address: str) -> Optional[Dict[str, Any]]:
        """Get token account information.
        
        Args:
            token_address: Token mint address
            owner_address: Token account owner address
            
        Returns:
            Token account information
        """
        try:
            token_pubkey = Pubkey.from_string(token_address)
            owner_pubkey = Pubkey.from_string(owner_address)
            
            # Get all token accounts owned by owner
            response = await self.connection.get_token_accounts_by_owner(
                owner_pubkey,
                {'mint': token_pubkey}
            )
            
            if not response.value:
                return None
                
            # Return first matching account
            return response.value[0].account.data
            
        except Exception as e:
            logger.error(f"Failed to get token account: {str(e)}")
            return None
            
    async def get_token_balance(self, token_address: str, owner_address: str) -> Optional[float]:
        """Get token balance for an account.
        
        Args:
            token_address: Token mint address
            owner_address: Token account owner address
            
        Returns:
            Token balance
        """
        try:
            account_info = await self.get_token_account(token_address, owner_address)
            if not account_info:
                return 0.0
                
            return float(account_info['amount']) / (10 ** account_info['decimals'])
            
        except Exception as e:
            logger.error(f"Failed to get token balance: {str(e)}")
            return None
            
    async def create_token_account(self, token_address: str, owner_address: str) -> Optional[str]:
        """Create a new token account.
        
        Args:
            token_address: Token mint address
            owner_address: Token account owner address
            
        Returns:
            New token account address
        """
        try:
            token_pubkey = Pubkey.from_string(token_address)
            owner_pubkey = Pubkey.from_string(owner_address)
            
            # Generate new account keypair
            account = Keypair()
            
            # Calculate minimum rent
            rent = await self.connection.get_minimum_balance_for_rent_exemption(
                self.program.account["Account"].size
            )
            
            # Build transaction
            tx = await self.program.rpc["initializeAccount"](
                ctx=Context(
                    accounts={
                        'account': account.public_key,
                        'mint': token_pubkey,
                        'owner': owner_pubkey,
                        'rent': RENT
                    },
                    signers=[account]
                )
            )
            
            return str(account.public_key)
            
        except Exception as e:
            logger.error(f"Failed to create token account: {str(e)}")
            return None
            
    async def transfer(self,
                      token_address: str,
                      from_address: str,
                      to_address: str,
                      amount: float,
                      decimals: int = 9) -> Optional[str]:
        """Transfer tokens between accounts.
        
        Args:
            token_address: Token mint address
            from_address: Source account address
            to_address: Destination account address
            amount: Amount to transfer
            decimals: Token decimals
            
        Returns:
            Transaction signature
        """
        try:
            # Convert amount to raw
            raw_amount = int(amount * (10 ** decimals))
            
            # Build transaction
            tx = await self.program.rpc["transfer"](
                raw_amount,
                ctx=Context(
                    accounts={
                        'source': Pubkey.from_string(from_address),
                        'destination': Pubkey.from_string(to_address),
                        'authority': self.wallet.public_key
                    }
                )
            )
            
            return tx['signature']
            
        except Exception as e:
            logger.error(f"Failed to transfer tokens: {str(e)}")
            return None
