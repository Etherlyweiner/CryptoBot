"""TokenScanner class for scanning new token launches"""
import logging
import asyncio
from typing import List, Dict, Optional
import aiohttp
import time
from datetime import datetime, timedelta
import base58

logger = logging.getLogger(__name__)

class TokenScanner:
    def __init__(self, config: Dict):
        """Initialize TokenScanner with configuration"""
        self.config = config
        self.rpc_url = config.get('helius', {}).get('rpc_url') or f"https://rpc.helius.xyz/?api-key={config['helius']['api_key']}"
        self.max_requests_per_minute = 60
        self.request_count = 0
        self.last_request_time = time.time()
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
    async def __aenter__(self):
        """Async context manager enter"""
        await self._get_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
        return self.session

    async def scan_new_tokens(self) -> List[Dict]:
        """Scan for new token launches"""
        try:
            session = await self._get_session()
            
            # Get recent transactions from Helius
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # Token Program
                    {
                        "limit": 100,
                        "commitment": "confirmed"
                    }
                ]
            }
            
            async with session.post(self.rpc_url, json=payload) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch signatures: {response.status}")
                    return []
                
                data = await response.json()
                if 'error' in data:
                    logger.error(f"RPC error: {data['error']}")
                    return []
                
                signatures = [tx['signature'] for tx in data.get('result', [])]
                
                # Get transaction details
                new_tokens = []
                for signature in signatures:
                    # Rate limiting
                    current_time = time.time()
                    if current_time - self.last_request_time >= 60:
                        self.request_count = 0
                        self.last_request_time = current_time
                    
                    if self.request_count >= self.max_requests_per_minute:
                        await asyncio.sleep(1)
                        continue
                    
                    tx_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getTransaction",
                        "params": [
                            signature,
                            {
                                "encoding": "jsonParsed",
                                "maxSupportedTransactionVersion": 0,
                                "commitment": "confirmed"
                            }
                        ]
                    }
                    
                    async with session.post(self.rpc_url, json=tx_payload) as tx_response:
                        if tx_response.status != 200:
                            continue
                        
                        tx_data = await tx_response.json()
                        if 'error' in tx_data:
                            continue
                        
                        result = tx_data.get('result', {})
                        if not result:
                            continue
                        
                        # Look for token creation
                        meta = result.get('meta', {})
                        if not meta:
                            continue
                            
                        post_token_balances = meta.get('postTokenBalances', [])
                        if not post_token_balances:
                            continue
                            
                        for balance in post_token_balances:
                            mint = balance.get('mint')
                            if mint:
                                # Get token info
                                token_info = await self._get_token_info(mint)
                                if token_info:
                                    new_tokens.append({
                                        'address': mint,
                                        'creation_slot': result.get('slot'),
                                        'owner': result.get('transaction', {}).get('message', {}).get('accountKeys', [])[0],
                                        'signature': signature,
                                        'decimals': token_info.get('decimals'),
                                        'supply': token_info.get('supply')
                                    })
                    
                    self.request_count += 1
                
                return new_tokens
                
        except Exception as e:
            logger.error(f"Error scanning for new tokens: {str(e)}")
            return []

    async def _get_token_info(self, token_address: str) -> Optional[Dict]:
        """Get token information using getAccountInfo"""
        try:
            session = await self._get_session()
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    token_address,
                    {
                        "encoding": "jsonParsed",
                        "commitment": "confirmed"
                    }
                ]
            }
            
            async with session.post(self.rpc_url, json=payload) as response:
                if response.status != 200:
                    return None
                    
                data = await response.json()
                if 'error' in data:
                    return None
                    
                result = data.get('result', {})
                if not result:
                    return None
                    
                account_data = result.get('value', {})
                if not account_data:
                    return None
                    
                parsed_data = account_data.get('data', {}).get('parsed', {}).get('info', {})
                if not parsed_data:
                    return None
                    
                return {
                    'decimals': parsed_data.get('decimals'),
                    'supply': parsed_data.get('supply'),
                    'mint_authority': parsed_data.get('mintAuthority'),
                    'freeze_authority': parsed_data.get('freezeAuthority')
                }
                
        except Exception as e:
            logger.error(f"Error getting token info: {str(e)}")
            return None

    async def close(self):
        """Close resources"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
