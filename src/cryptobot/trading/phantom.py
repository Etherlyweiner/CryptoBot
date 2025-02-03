"""
Phantom Wallet Integration for CryptoBot
"""

import os
import json
import base64
from typing import Dict, Optional, List
import aiohttp
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from ..monitoring.logger import BotLogger
from ..config.manager import ConfigurationManager
from dotenv import load_dotenv

class PhantomWallet:
    """Integration with Phantom Wallet."""
    
    def __init__(self):
        """Initialize Phantom wallet connection."""
        self.logger = BotLogger()
        load_dotenv()  # Load environment variables
        self.client = None
        self.wallet_address = os.getenv('PHANTOM_WALLET_ADDRESS')
        self.connected = False
        
    async def initialize(self) -> bool:
        """Initialize connection to Phantom wallet."""
        try:
            if not self.wallet_address:
                self.logger.error("Phantom wallet address not configured")
                return False
                
            # Initialize Solana client
            endpoint = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
            self.client = AsyncClient(endpoint, Confirmed)
            
            # Verify wallet connection
            if await self.verify_connection():
                self.connected = True
                self.logger.info(f"Connected to Phantom wallet: {self.wallet_address}")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to initialize Phantom wallet: {str(e)}")
            return False
            
    async def verify_connection(self) -> bool:
        """Verify connection to Phantom wallet."""
        try:
            if not self.wallet_address or not self.client:
                return False
                
            # Check if the wallet exists and is accessible
            response = await self.client.get_account_info(self.wallet_address)
            return response.get('result') is not None
            
        except Exception as e:
            self.logger.error(f"Failed to verify Phantom wallet connection: {str(e)}")
            return False
            
    async def get_token_accounts(self) -> List[Dict]:
        """Get all token accounts associated with the wallet."""
        try:
            if not self.connected:
                return []
                
            response = await self.client.get_token_accounts_by_owner(
                self.wallet_address,
                {'programId': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'}
            )
            
            accounts = []
            for item in response.get('result', {}).get('value', []):
                try:
                    data = base64.b64decode(item['account']['data'][0])
                    mint = data[0:32].hex()
                    accounts.append({
                        'mint': mint,
                        'address': item['pubkey'],
                        'amount': int.from_bytes(data[64:72], 'little') / 1e9
                    })
                except Exception as e:
                    self.logger.warning(f"Failed to parse token account: {str(e)}")
                    
            return accounts
            
        except Exception as e:
            self.logger.error(f"Failed to get token accounts: {str(e)}")
            return []
            
    async def get_memecoin_balances(self) -> Dict[str, float]:
        """Get balances of known memecoins."""
        try:
            accounts = await self.get_token_accounts()
            
            # Define known memecoin addresses (add more as needed)
            memecoin_addresses = {
                'BONK': '7rVfg4Gn4dJv9kbNyhfxEJHwfP82E7vh3N4zQgRrCXvi',
                'WIF': 'EKLNDx4pQ8eWKc2WpkuFpEZr4XpRqZyFc4WiKgnfpz7N',
                'MYRO': 'HMYHrQemZLWSXgGGSxwPZcU1qRYqKzxRUC7eb9tEeCbu'
            }
            
            balances = {}
            for account in accounts:
                for token_name, token_address in memecoin_addresses.items():
                    if account['mint'] == token_address:
                        balances[token_name] = account['amount']
                        
            return balances
            
        except Exception as e:
            self.logger.error(f"Failed to get memecoin balances: {str(e)}")
            return {}
            
    async def get_memecoin_prices(self) -> Dict[str, float]:
        """Get current prices for memecoins from Jupiter aggregator."""
        try:
            async with aiohttp.ClientSession() as session:
                # Use Jupiter API to get price data
                async with session.get('https://price.jup.ag/v4/price', params={
                    'ids': 'BONK,WIF,MYRO'
                }) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            token: float(info['price'])
                            for token, info in data.get('data', {}).items()
                        }
            return {}
        except Exception as e:
            self.logger.error(f"Failed to get memecoin prices: {str(e)}")
            return {}
