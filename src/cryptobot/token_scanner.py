"""TokenScanner class for scanning new token launches"""
import logging
import asyncio
from typing import List, Dict, Optional
import aiohttp
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TokenScanner:
    def __init__(self, config: Dict):
        """Initialize TokenScanner with configuration"""
        self.rpc_url = config.get('helius', {}).get('rpc_url') or f"https://rpc.helius.xyz/?api-key={config['helius']['api_key']}"
        self.max_requests_per_minute = 60
        self.request_count = 0
        self.last_request_time = time.time()
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
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

    async def scan_new_tokens(self, max_market_cap: float = 1000000) -> List[Dict]:
        """Scan for new token launches on Solana"""
        try:
            # Rate limiting check
            await self._handle_rate_limit()
            
            # Get recently created token accounts
            new_tokens = await self._get_recent_token_creations()
            
            # Filter and enrich token data
            valid_tokens = []
            for token in new_tokens:
                # Check market cap
                token_info = await self._get_token_info(token['address'])
                if token_info and token_info.get('market_cap', float('inf')) <= max_market_cap:
                    # Enrich with additional data
                    token_data = {
                        **token,
                        **token_info,
                        'launch_date': datetime.now().isoformat(),
                        'initial_analysis': await self._analyze_token(token['address'])
                    }
                    valid_tokens.append(token_data)
                    
            return valid_tokens
            
        except Exception as e:
            logger.error(f"Error scanning new tokens: {str(e)}")
            return []
            
    async def _handle_rate_limit(self):
        """Handle API rate limiting"""
        current_time = time.time()
        if current_time - self.last_request_time >= 60:
            self.request_count = 0
            self.last_request_time = current_time
            
        if self.request_count >= self.max_requests_per_minute:
            wait_time = 60 - (current_time - self.last_request_time)
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                self.request_count = 0
                self.last_request_time = time.time()
                
        self.request_count += 1
        
    async def _get_recent_token_creations(self) -> List[Dict]:
        """Get recently created token accounts"""
        try:
            session = await self._get_session()
            
            # Query Solana for recent token program interactions
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getProgramAccounts",
                "params": [
                    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                    {
                        "encoding": "jsonParsed",
                        "filters": [
                            {"dataSize": 82},  # Size of token account data
                            {"memcmp": {"offset": 0, "bytes": "2"}}  # Filter for mint accounts
                        ]
                    }
                ]
            }
            
            async with session.post(self.rpc_url, json=payload) as response:
                if response.status == 429:  # Too Many Requests
                    logger.warning("Rate limit hit, implementing backoff")
                    await asyncio.sleep(5)
                    return await self._get_recent_token_creations()
                    
                data = await response.json()
                if 'result' not in data:
                    logger.error(f"Unexpected response: {data}")
                    return []
                    
                return [
                    {
                        'address': account['pubkey'],
                        'creation_slot': account.get('slot'),
                        'owner': account['account']['owner']
                    }
                    for account in data['result']
                ]
                
        except Exception as e:
            logger.error(f"Error getting recent token creations: {str(e)}")
            return []
            
    async def _get_token_info(self, token_address: str) -> Optional[Dict]:
        """Get detailed token information"""
        try:
            session = await self._get_session()
            
            # Query Jupiter API for token info
            url = f"https://price.jup.ag/v4/price?ids={token_address}"
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                    
                data = await response.json()
                return {
                    'price': float(data.get('data', {}).get(token_address, {}).get('price', 0)),
                    'market_cap': float(data.get('data', {}).get(token_address, {}).get('marketCap', 0)),
                    'liquidity': float(data.get('data', {}).get(token_address, {}).get('liquidityInUsd', 0))
                }
                
        except Exception as e:
            logger.error(f"Error getting token info: {str(e)}")
            return None
            
    async def _analyze_token(self, token_address: str) -> Dict:
        """Perform initial token analysis"""
        try:
            # Get holder information
            holders = await self._get_holder_info(token_address)
            
            # Get recent trades
            trades = await self._get_recent_trades(token_address)
            
            return {
                'holder_count': holders.get('count', 0),
                'top_holder_percentage': holders.get('top_percentage', 0),
                'trade_count_24h': trades.get('count_24h', 0),
                'avg_trade_size': trades.get('avg_size', 0),
                'risk_score': self._calculate_risk_score(holders, trades)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing token: {str(e)}")
            return {}
            
    async def _get_holder_info(self, token_address: str) -> Dict:
        """Get token holder information"""
        try:
            session = await self._get_session()
            
            # Query token holder program
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenLargestAccounts",
                "params": [token_address]
            }
            
            async with session.post(self.rpc_url, json=payload) as response:
                data = await response.json()
                if 'result' not in data:
                    return {'count': 0, 'top_percentage': 0}
                    
                holders = data['result']['value']
                total_supply = sum(float(h['uiAmount']) for h in holders)
                top_holder_amount = float(holders[0]['uiAmount']) if holders else 0
                
                return {
                    'count': len(holders),
                    'top_percentage': (top_holder_amount / total_supply * 100) if total_supply > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Error getting holder info: {str(e)}")
            return {'count': 0, 'top_percentage': 0}
            
    async def _get_recent_trades(self, token_address: str) -> Dict:
        """Get recent trade information"""
        try:
            # Implement trade history fetching
            return {
                'count_24h': 0,
                'avg_size': 0
            }
        except Exception as e:
            logger.error(f"Error getting recent trades: {str(e)}")
            return {'count_24h': 0, 'avg_size': 0}
            
    def _calculate_risk_score(self, holders: Dict, trades: Dict) -> float:
        """Calculate risk score based on holder and trade metrics"""
        try:
            # Risk factors
            holder_count_score = min(1.0, holders.get('count', 0) / 1000)
            concentration_score = 1.0 - (holders.get('top_percentage', 100) / 100)
            trade_activity_score = min(1.0, trades.get('count_24h', 0) / 100)
            
            # Weighted average
            weights = {
                'holder_count': 0.3,
                'concentration': 0.4,
                'trade_activity': 0.3
            }
            
            risk_score = (
                holder_count_score * weights['holder_count'] +
                concentration_score * weights['concentration'] +
                trade_activity_score * weights['trade_activity']
            )
            
            return round(risk_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            return 0.0
            
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
